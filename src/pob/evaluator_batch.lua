-- Batch Evaluator for Persistent Worker Pool
--
-- This script initialises PoB once and then serves evaluation requests over
-- stdin/stdout for the lifetime of the process.
--
-- Protocol (one request line in, one JSON line out):
--
--   <base64 xml>            Legacy: full reload of a build from XML and
--                           evaluation (~3-5 s per call).
--   LOAD <base64 xml>       Load a build as the *session base* and evaluate
--                           it. All later SET/DELTA calls operate on this build
--                           (items, gems, config stay fixed; only the passive
--                           tree changes).
--   SET <json>              {"nodes":[ids], "masteries":{"nodeId":effectId}}
--                           Replace the session tree in place and evaluate
--                           (~0.8-1 s). The new tree becomes the base for
--                           later DELTA calls.
--   DELTA <json>            {"add":[ids], "remove":[ids],
--                            "masteries":{"nodeId":effectId}}
--                           Evaluate a modification of the session tree
--                           WITHOUT changing it (~0.15-0.35 s). Uses PoB's
--                           own incremental "misc calculator" (the same code
--                           path that powers node hover tooltips).
--                           - "remove" removes each node and every node that
--                             depends on it for connectivity (same as
--                             unallocating it in the PoB UI).
--                           - "add" allocates each node and its shortest path
--                             to the current tree.
--                           - "masteries" temporarily overrides mastery
--                             effect selections.
--   IMPORT <base64 json>    Import a character through PoB's own ImportTab
--                           (items, gems, tree, jewels, cluster nodes,
--                           tattoos, bloodline ascendancy). Reply carries
--                           the resulting build as base64 XML plus stats.
--   PING                    -> {"pong":true}
--   EXIT                    -> {"exit":true} and terminate.
--
-- Every evaluation reply has the shape:
--   {"success":true, "stats":{...}, "pointsUsed":N}
-- or
--   {"success":false, "error":"..."}
--
-- PoB's own console output (ConPrintf) is silenced after start-up so that
-- stdout carries only protocol lines.

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"

local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

-- Route all of PoB's console output to stderr. HeadlessWrapper's ConPrintf
-- calls print(), and stdout is our protocol channel.
local rawPrint = print
print = function(...)
    local parts = {}
    for i = 1, select("#", ...) do
        parts[#parts + 1] = tostring((select(i, ...)))
    end
    io.stderr:write(table.concat(parts, "\t") .. "\n")
end

-- Load HeadlessWrapper
dofile("HeadlessWrapper.lua")

-- Override HeadlessWrapper stubs for timeless jewel data loading
function GetScriptPath()
    return "."
end

function NewFileSearch(pattern)
    local filepath = pattern:gsub("%*", "")
    local file = io.open(filepath, "rb")
    if not file then
        return nil
    end
    file:close()

    local handle = {
        filepath = filepath,
        filename = filepath:match("([^/]+)$") or filepath,
        done = false
    }

    function handle:GetFileName()
        return self.filename
    end

    function handle:GetFileModifiedTime()
        if self.filepath:match("%.bin$") then
            return 2000000000
        elseif self.filepath:match("%.zip") then
            return 1000000000
        end
        return os.time()
    end

    function handle:NextFile()
        self.done = true
        return false
    end

    return handle
end

-- Keep PoB console chatter (e.g. "Missing LUT: Lethal Pride") on stderr so it
-- is available for debugging without polluting the protocol stream.
function ConPrintf(fmt, ...)
    local ok, msg = pcall(string.format, fmt, ...)
    io.stderr:write((ok and msg or tostring(fmt)) .. "\n")
end

-- Signal ready to parent process
io.stdout:write('{"ready":true}\n')
io.stdout:flush()

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

local function safeGet(output, key, default)
    local value = output[key]
    if value == nil or type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then
        return default or 0
    end
    return math.floor(value * 100 + 0.5) / 100
end

local function encodeJSON(obj)
    local function encodeValue(val)
        local t = type(val)
        if t == "string" then
            return '"' .. val:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n') .. '"'
        elseif t == "number" then
            if val ~= val or val == math.huge or val == -math.huge then
                return "0"
            end
            return tostring(val)
        elseif t == "boolean" then
            return val and "true" or "false"
        elseif t == "table" then
            local parts = {}
            if #val > 0 or next(val) == nil then
                -- array (or empty table)
                for _, v in ipairs(val) do
                    table.insert(parts, encodeValue(v))
                end
                return "[" .. table.concat(parts, ",") .. "]"
            end
            for k, v in pairs(val) do
                table.insert(parts, '"' .. tostring(k) .. '":' .. encodeValue(v))
            end
            return "{" .. table.concat(parts, ",") .. "}"
        else
            return "null"
        end
    end
    return encodeValue(obj)
end

-- Minimal JSON decoder: enough for the request objects we accept
-- (objects, arrays, numbers, strings without escapes beyond \" and \\, booleans, null).
local function decodeJSON(str)
    local pos = 1
    local function skipWs()
        pos = str:find("%S", pos) or (#str + 1)
    end
    local parseValue
    local function parseString()
        pos = pos + 1 -- opening quote
        local out = {}
        while pos <= #str do
            local c = str:sub(pos, pos)
            if c == '"' then
                pos = pos + 1
                return table.concat(out)
            elseif c == "\\" then
                local n = str:sub(pos + 1, pos + 1)
                if n == "n" then out[#out + 1] = "\n"
                elseif n == "t" then out[#out + 1] = "\t"
                else out[#out + 1] = n end
                pos = pos + 2
            else
                out[#out + 1] = c
                pos = pos + 1
            end
        end
        error("unterminated string")
    end
    local function parseNumber()
        local s, e = str:find("^-?%d+%.?%d*[eE]?[-+]?%d*", pos)
        local num = tonumber(str:sub(s, e))
        pos = e + 1
        return num
    end
    local function parseArray()
        pos = pos + 1
        local arr = {}
        skipWs()
        if str:sub(pos, pos) == "]" then pos = pos + 1; return arr end
        while true do
            skipWs()
            arr[#arr + 1] = parseValue()
            skipWs()
            local c = str:sub(pos, pos)
            if c == "," then pos = pos + 1
            elseif c == "]" then pos = pos + 1; return arr
            else error("expected , or ] at " .. pos) end
        end
    end
    local function parseObject()
        pos = pos + 1
        local obj = {}
        skipWs()
        if str:sub(pos, pos) == "}" then pos = pos + 1; return obj end
        while true do
            skipWs()
            local key = parseString()
            skipWs()
            if str:sub(pos, pos) ~= ":" then error("expected : at " .. pos) end
            pos = pos + 1
            skipWs()
            obj[key] = parseValue()
            skipWs()
            local c = str:sub(pos, pos)
            if c == "," then pos = pos + 1
            elseif c == "}" then pos = pos + 1; return obj
            else error("expected , or } at " .. pos) end
        end
    end
    parseValue = function()
        skipWs()
        local c = str:sub(pos, pos)
        if c == "{" then return parseObject()
        elseif c == "[" then return parseArray()
        elseif c == '"' then return parseString()
        elseif str:sub(pos, pos + 3) == "true" then pos = pos + 4; return true
        elseif str:sub(pos, pos + 4) == "false" then pos = pos + 5; return false
        elseif str:sub(pos, pos + 3) == "null" then pos = pos + 4; return nil
        else return parseNumber() end
    end
    return parseValue()
end

local b64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
local function base64_decode(data)
    data = data:gsub('[^'..b64chars..'=]', '')
    return (data:gsub('.', function(x)
        if x == '=' then return '' end
        local r, f = '', (b64chars:find(x) - 1)
        for i = 6, 1, -1 do
            r = r .. (f % 2^i - f % 2^(i-1) > 0 and '1' or '0')
        end
        return r
    end):gsub('%d%d%d?%d?%d?%d?%d?%d?', function(x)
        if #x ~= 8 then return '' end
        local c = 0
        for i = 1, 8 do
            c = c + (x:sub(i, i) == '1' and 2^(8-i) or 0)
        end
        return string.char(c)
    end))
end

local function extractStats(output)
    return {
        totalDPS = safeGet(output, "TotalDPS"),
        combinedDPS = safeGet(output, "CombinedDPS"),
        totalDotDPS = safeGet(output, "TotalDotDPS"),
        fullDPS = safeGet(output, "FullDPS"),
        averageDamage = safeGet(output, "AverageDamage"),
        speed = safeGet(output, "Speed"),
        hitChance = safeGet(output, "AccuracyHitChance"),
        critChance = safeGet(output, "CritChance"),
        totalEHP = safeGet(output, "TotalEHP"),
        life = safeGet(output, "Life"),
        energyShield = safeGet(output, "EnergyShield"),
        mana = safeGet(output, "Mana"),
        armour = safeGet(output, "Armour"),
        evasion = safeGet(output, "Evasion"),
        blockChance = safeGet(output, "BlockChance"),
        fireRes = safeGet(output, "FireResist"),
        coldRes = safeGet(output, "ColdResist"),
        lightningRes = safeGet(output, "LightningResist"),
        chaosRes = safeGet(output, "ChaosResist"),
        strength = safeGet(output, "Str"),
        dexterity = safeGet(output, "Dex"),
        intelligence = safeGet(output, "Int"),
    }
end

local function allocatedNodeIds(spec, removeSet, addSet)
    local ids = {}
    for id, node in pairs(spec.allocNodes) do
        if not (removeSet and removeSet[node]) then
            ids[#ids + 1] = id
        end
    end
    if addSet then
        for node in pairs(addSet) do
            ids[#ids + 1] = node.id
        end
    end
    table.sort(ids)
    return ids
end

local function countPoints(spec)
    local used = 0
    for _, node in pairs(spec.allocNodes) do
        if node.type ~= "ClassStart" and node.type ~= "AscendClassStart" and not node.ascendancyName then
            used = used + 1
        end
    end
    return used
end

-- ---------------------------------------------------------------------------
-- Full-reload evaluation (legacy path, also used by LOAD)
-- ---------------------------------------------------------------------------

local function loadBuild(xmlContent)
    loadBuildFromXML(xmlContent, "BatchBuild")

    for i = 1, 5 do
        runCallback("OnFrame")
    end

    -- Manual tree load workaround: HeadlessWrapper doesn't always call
    -- TreeTab:Load(), leaving specList empty.
    if build and build.treeTab and build.treeTab.specList and #build.treeTab.specList == 0 then
        local xmlModule = require("xml")
        local parsed = xmlModule.ParseXML(xmlContent)

        if parsed and parsed[1] then
            for _, node in ipairs(parsed[1]) do
                if type(node) == "table" and node.elem == "Tree" then
                    pcall(function()
                        build.treeTab:Load(node, nil)
                    end)
                    if build.treeTab.PostLoad then
                        pcall(function()
                            build.treeTab:PostLoad()
                        end)
                    end
                    break
                end
            end
        end

        if #build.treeTab.specList == 0 then
            return false, "Tree load failed"
        end
    end

    if build and build.calcsTab and build.calcsTab.BuildOutput then
        build.buildFlag = true
        build.calcsTab:BuildOutput()
    end

    runCallback("OnFrame")

    if not (build and build.calcsTab and build.calcsTab.mainOutput) then
        return false, "No output available"
    end
    return true
end

local function evaluateBuild(xmlContent)
    local ok, err = loadBuild(xmlContent)
    if not ok then
        return {success = false, error = err}
    end
    return {
        success = true,
        stats = extractStats(build.calcsTab.mainOutput),
        pointsUsed = countPoints(build.spec),
    }
end

-- ---------------------------------------------------------------------------
-- Session (incremental) evaluation
-- ---------------------------------------------------------------------------

local session = {
    loaded = false,
    calcFunc = nil,
}

local function sessionRebuildCalculator()
    local calcFunc = build.calcsTab:GetMiscCalculator()
    session.calcFunc = calcFunc
end

local function sessionLoad(xmlContent)
    local ok, err = loadBuild(xmlContent)
    if not ok then
        session.loaded = false
        return {success = false, error = err}
    end
    sessionRebuildCalculator()
    session.loaded = true
    local output = session.calcFunc({})
    return {
        success = true,
        stats = extractStats(output),
        pointsUsed = countPoints(build.spec),
        nodes = allocatedNodeIds(build.spec),
    }
end

local function toMasteryTable(masteries)
    local out = {}
    if masteries then
        for k, v in pairs(masteries) do
            local id = tonumber(k)
            local eff = tonumber(v)
            if id and eff then
                out[id] = eff
            end
        end
    end
    return out
end

local function currentMasteries(spec)
    local out = {}
    for k, v in pairs(spec.masterySelections) do
        out[k] = v
    end
    return out
end

-- PoB v2.61+ added a leading optional `className` parameter to
-- PassiveSpec:ImportFromNodeList. Detect the arity once so both signatures work.
local importNodeListHasClassName = nil
local function importNodeList(spec, nodeList, masteries)
    if importNodeListHasClassName == nil then
        local info = debug.getinfo(spec.ImportFromNodeList, "u")
        -- self + 8 params in the new signature, self + 7 in the old one
        importNodeListHasClassName = (info and info.nparams or 8) >= 9
    end
    if importNodeListHasClassName then
        spec:ImportFromNodeList(
            nil,
            spec.curClassId,
            spec.curAscendClassId,
            spec.curSecondaryAscendClassId or 0,
            nodeList,
            spec.hashOverrides,
            masteries
        )
    else
        spec:ImportFromNodeList(
            spec.curClassId,
            spec.curAscendClassId,
            spec.curSecondaryAscendClassId or 0,
            nodeList,
            spec.hashOverrides,
            masteries
        )
    end
end

-- Replace the session tree in place.
local function sessionSet(req)
    if not session.loaded then
        return {success = false, error = "No session loaded (send LOAD first)"}
    end
    local spec = build.spec
    local nodeList = {}
    for _, id in ipairs(req.nodes or {}) do
        nodeList[#nodeList + 1] = tonumber(id)
    end
    local masteries = req.masteries and toMasteryTable(req.masteries) or currentMasteries(spec)

    importNodeList(spec, nodeList, masteries)
    -- Keep the build's "official" output in sync so any later full-reload
    -- consumers (and mainEnv-based lookups) see the new tree.
    build.buildFlag = true
    local output = session.calcFunc({})
    return {
        success = true,
        stats = extractStats(output),
        pointsUsed = countPoints(spec),
        nodes = allocatedNodeIds(spec),
    }
end

-- Evaluate a modification relative to the session tree without changing it.
local function sessionDelta(req)
    if not session.loaded then
        return {success = false, error = "No session loaded (send LOAD first)"}
    end
    local spec = build.spec
    local override = {}
    local addNodes, removeNodes = {}, {}
    local addCount, removeCount = 0, 0
    local haveAdd, haveRemove = false, false

    for _, rawId in ipairs(req.remove or {}) do
        local node = spec.nodes[tonumber(rawId)]
        if not node then
            return {success = false, error = "Unknown node " .. tostring(rawId)}
        end
        if node.type == "ClassStart" or node.type == "AscendClassStart" then
            return {success = false, error = "Cannot remove start node " .. tostring(rawId)}
        end
        if node.alloc then
            -- node.depends = the node itself plus every node that is only
            -- connected to the tree through it.
            for _, dep in ipairs(node.depends or {node}) do
                if not removeNodes[dep] and dep.type ~= "ClassStart" and dep.type ~= "AscendClassStart" then
                    removeNodes[dep] = true
                    removeCount = removeCount + 1
                    haveRemove = true
                end
            end
        end
    end

    for _, rawId in ipairs(req.add or {}) do
        local node = spec.nodes[tonumber(rawId)]
        if not node then
            return {success = false, error = "Unknown node " .. tostring(rawId)}
        end
        if not node.alloc then
            if not node.path then
                return {success = false, error = "Node " .. tostring(rawId) .. " is unreachable"}
            end
            for _, pathNode in ipairs(node.path) do
                if not pathNode.alloc and not addNodes[pathNode] then
                    addNodes[pathNode] = true
                    addCount = addCount + 1
                    haveAdd = true
                end
            end
        end
    end

    if haveAdd then override.addNodes = addNodes end
    if haveRemove then override.removeNodes = removeNodes end

    -- Temporary mastery overrides
    local patched = {}
    local masteries = req.masteries and toMasteryTable(req.masteries) or nil
    if masteries then
        for id, effectId in pairs(masteries) do
            local node = spec.nodes[id]
            local effect = spec.tree.masteryEffects[effectId]
            if node and effect and node.type == "Mastery" then
                patched[#patched + 1] = {
                    node = node,
                    sd = node.sd,
                    allMasteryOptions = node.allMasteryOptions,
                    selection = spec.masterySelections[id],
                    mods = node.mods,
                    modList = node.modList,
                    modKey = node.modKey,
                }
                node.sd = effect.sd
                node.allMasteryOptions = false
                spec.tree:ProcessStats(node)
                spec.masterySelections[id] = effectId
                if not node.alloc and not addNodes[node] then
                    -- Selecting an effect on an unallocated mastery implies allocating it
                    addNodes[node] = true
                    addCount = addCount + 1
                    override.addNodes = addNodes
                end
            end
        end
    end

    local ok, output = pcall(session.calcFunc, override)

    -- Restore mastery state
    for _, p in ipairs(patched) do
        p.node.sd = p.sd
        p.node.allMasteryOptions = p.allMasteryOptions
        p.node.mods = p.mods
        p.node.modList = p.modList
        p.node.modKey = p.modKey
        spec.masterySelections[p.node.id] = p.selection
    end

    if not ok then
        return {success = false, error = "Calculation failed: " .. tostring(output)}
    end

    return {
        success = true,
        stats = extractStats(output),
        pointsUsed = countPoints(spec) - removeCount + addCount,
        added = addCount,
        removed = removeCount,
        nodes = allocatedNodeIds(spec, haveRemove and removeNodes or nil, (haveAdd or next(addNodes)) and addNodes or nil),
    }
end

-- ---------------------------------------------------------------------------
-- Character import through PoB's own importer
-- ---------------------------------------------------------------------------

local b64chars_enc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
local function base64_encode(data)
    return ((data:gsub('.', function(x)
        local r, b = '', x:byte()
        for i = 8, 1, -1 do r = r .. (b % 2^i - b % 2^(i-1) > 0 and '1' or '0') end
        return r
    end) .. '0000'):gsub('%d%d%d?%d?%d?%d?', function(x)
        if #x < 6 then return '' end
        local c = 0
        for i = 1, 6 do c = c + (x:sub(i, i) == '1' and 2^(6-i) or 0) end
        return b64chars_enc:sub(c+1, c+1)
    end) .. ({ '', '==', '=' })[#data % 3 + 1])
end

-- Pick the socket group most likely to be the main skill: the group with the
-- most non-support gems, preferring the body armour on ties. PoB's importer
-- deliberately leaves this unset.
local function chooseMainSocketGroup()
    local bestIdx, bestScore = 1, -1
    for i, group in ipairs(build.skillsTab.socketGroupList or {}) do
        local actives, supports = 0, 0
        for _, gem in ipairs(group.gemList or {}) do
            if gem.grantedEffect then
                if gem.grantedEffect.support then supports = supports + 1 else actives = actives + 1 end
            end
        end
        if actives > 0 then
            local score = supports * 10 + actives + ((group.slot == "Body Armour") and 5 or 0)
            if score > bestScore then bestIdx, bestScore = i, score end
        end
    end
    return bestIdx
end

-- IMPORT <base64 json>: the character object PoB's ImportTab expects
-- ({name, class, league, level, equipment=[items], jewels=[items], passives={...}}).
-- Replies with PoB's own XML for the imported build plus its stats.
local function importCharacter(jsonText)
    local ok, err = pcall(loadBuildFromJSON, jsonText)
    if not ok then
        return {success = false, error = "PoB import failed: " .. tostring(err)}
    end
    for i = 1, 5 do runCallback("OnFrame") end
    if build and build.skillsTab then
        build.mainSocketGroup = chooseMainSocketGroup()
    end
    build.buildFlag = true
    build.calcsTab:BuildOutput()
    runCallback("OnFrame")
    local okSave, xmlText = pcall(function() return build:SaveDB("import") end)
    if not okSave or not xmlText then
        return {success = false, error = "PoB could not serialise the imported build: " .. tostring(xmlText)}
    end
    session.loaded = false
    local output = build.calcsTab.mainOutput or {}
    return {
        success = true,
        xml = base64_encode(xmlText),
        stats = extractStats(output),
        pointsUsed = countPoints(build.spec),
        mainSocketGroup = build.mainSocketGroup,
    }
end

-- ---------------------------------------------------------------------------
-- Main loop
-- ---------------------------------------------------------------------------

local function respond(tbl)
    io.stdout:write(encodeJSON(tbl) .. '\n')
    io.stdout:flush()
end

local function handleJSONCommand(payload, handler)
    local ok, req = pcall(decodeJSON, payload)
    if not ok or type(req) ~= "table" then
        return {success = false, error = "Invalid JSON request: " .. tostring(req)}
    end
    local ok2, result = pcall(handler, req)
    if not ok2 then
        return {success = false, error = "Request failed: " .. tostring(result)}
    end
    return result
end

while true do
    local line = io.read("*l")

    if not line then
        break
    end

    if line == "EXIT" then
        respond({exit = true})
        break
    elseif line == "PING" then
        respond({pong = true})
    elseif line:sub(1, 5) == "LOAD " then
        local ok, xmlContent = pcall(base64_decode, line:sub(6))
        if not ok or not xmlContent or xmlContent == "" then
            respond({success = false, error = "Failed to decode base64 input"})
        else
            local ok2, result = pcall(sessionLoad, xmlContent)
            respond(ok2 and result or {success = false, error = "Load failed: " .. tostring(result)})
        end
    elseif line:sub(1, 7) == "IMPORT " then
        local ok, jsonText = pcall(base64_decode, line:sub(8))
        if not ok or not jsonText or jsonText == "" then
            respond({success = false, error = "Failed to decode base64 input"})
        else
            local ok2, result = pcall(importCharacter, jsonText)
            respond(ok2 and result or {success = false, error = "Import failed: " .. tostring(result)})
        end
    elseif line:sub(1, 4) == "SET " then
        respond(handleJSONCommand(line:sub(5), sessionSet))
    elseif line:sub(1, 6) == "DELTA " then
        respond(handleJSONCommand(line:sub(7), sessionDelta))
    elseif line ~= "" then
        -- Legacy: bare base64 XML
        local ok, xmlContent = pcall(base64_decode, line)
        if not ok or not xmlContent or xmlContent == "" then
            respond({success = false, error = "Failed to decode base64 input"})
        else
            local ok2, result = pcall(evaluateBuild, xmlContent)
            respond(ok2 and result or {success = false, error = "Evaluation failed: " .. tostring(result)})
            -- A legacy full reload replaces the session build
            if ok2 and result.success and session.loaded then
                pcall(sessionRebuildCalculator)
            end
        end
    end
end
