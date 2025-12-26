-- Batch Evaluator for Persistent Worker Pool
-- This script initializes PoB once and processes multiple builds via stdin/stdout
-- Protocol:
--   Input:  One line per build - base64-encoded XML (to avoid newline issues)
--   Output: One JSON line per build with stats
--   Exit:   Send "EXIT" to terminate the worker

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"

local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
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

-- Initialize PoB (this is the expensive part - only done once!)
runCallback("OnInit")
runCallback("OnFrame")

-- Signal ready to parent process
io.stdout:write('{"ready":true}\n')
io.stdout:flush()

-- Helper: Safe value extraction
local function safeGet(output, key, default)
    local value = output[key]
    if value == nil or type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then
        return default or 0
    end
    return math.floor(value * 100 + 0.5) / 100
end

-- Helper: Simple JSON encoder
local function encodeJSON(obj)
    local function encodeValue(val)
        local t = type(val)
        if t == "string" then
            return '"' .. val:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n') .. '"'
        elseif t == "number" then
            return tostring(val)
        elseif t == "boolean" then
            return val and "true" or "false"
        elseif t == "table" then
            local parts = {}
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

-- Helper: Base64 decode
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

-- Helper: Evaluate a build and return stats
local function evaluateBuild(xmlContent)
    -- Load the build
    loadBuildFromXML(xmlContent, "BatchBuild")

    -- Give frames to initialize
    for i = 1, 5 do
        runCallback("OnFrame")
    end

    -- Manual tree load workaround if specList is empty
    -- (PoB's HeadlessWrapper doesn't always call TreeTab:Load automatically)
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
            return {success = false, error = "Tree load failed"}
        end
    end

    -- Force calculation
    if build and build.calcsTab and build.calcsTab.BuildOutput then
        build.buildFlag = true
        build.calcsTab:BuildOutput()
    end

    runCallback("OnFrame")

    -- Extract statistics
    local output = build and build.calcsTab and build.calcsTab.mainOutput
    if not output then
        return {success = false, error = "No output available"}
    end

    local stats = {
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

    return {success = true, stats = stats}
end

-- Main loop - process builds from stdin
while true do
    local line = io.read("*l")

    if not line then
        -- EOF - parent process closed stdin
        break
    end

    if line == "EXIT" then
        -- Clean exit requested
        io.stdout:write('{"exit":true}\n')
        io.stdout:flush()
        break
    end

    if line == "PING" then
        -- Health check
        io.stdout:write('{"pong":true}\n')
        io.stdout:flush()
    elseif line ~= "" then
        -- Decode base64 XML and evaluate
        local success, xmlContent = pcall(base64_decode, line)

        if not success or not xmlContent or xmlContent == "" then
            io.stdout:write('{"success":false,"error":"Failed to decode base64 input"}\n')
        else
            local result = evaluateBuild(xmlContent)
            io.stdout:write(encodeJSON(result) .. '\n')
        end
        io.stdout:flush()
    end
end
