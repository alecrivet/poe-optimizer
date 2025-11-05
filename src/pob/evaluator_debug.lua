-- Debug version of PoB Build Evaluator
-- Outputs tree information to diagnose why node removal doesn't change stats

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"

local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

local buildXMLPath = arg[1]

if not buildXMLPath then
    io.stderr:write('{"success":false,"error":"No build XML file specified"}\n')
    os.exit(1)
end

local file = io.open(buildXMLPath, "r")
if not file then
    io.stderr:write('{"success":false,"error":"Cannot open file: ' .. buildXMLPath .. '"}\n')
    os.exit(1)
end
local xmlContent = file:read("*all")
file:close()

-- Load HeadlessWrapper
local headless_success, headless_err = pcall(function()
    dofile("HeadlessWrapper.lua")
end)

if not headless_success then
    io.stderr:write('{"success":false,"error":"Failed to load HeadlessWrapper: ' .. tostring(headless_err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

-- Load the build
local success, err = pcall(function()
    loadBuildFromXML(xmlContent, "EvaluatedBuild")
end)

if not success then
    io.stderr:write('{"success":false,"error":"Failed to load build: ' .. tostring(err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

-- Trigger calculations
for i = 1, 3 do
    runCallback("OnFrame")
end

if build and build.calcsTab and build.calcsTab.BuildOutput then
    local calc_success, calc_err = pcall(function()
        build.buildFlag = true
        build.calcsTab:BuildOutput()
    end)

    if not calc_success then
        io.stderr:write('{"success":false,"error":"Failed to trigger calculations: ' .. tostring(calc_err):gsub('"', '\\"') .. '"}\n')
        os.exit(1)
    end
end

runCallback("OnFrame")

-- Extract statistics
local output = build and build.calcsTab and build.calcsTab.mainOutput
if not output then
    io.stderr:write('{"success":false,"error":"Build calculations failed - no output available"}\n')
    os.exit(1)
end

-- Helper function to safely get values
local function safeGet(output, key, default)
    local value = output[key]
    if value == nil then
        return default or 0
    end
    if type(value) ~= "number" then
        return default or 0
    end
    if value ~= value then
        return default or 0
    end
    if value == math.huge or value == -math.huge then
        return default or 0
    end
    return math.floor(value * 100 + 0.5) / 100
end

-- BUILD THE DEBUG INFO: Count passive tree nodes
local treeNodeCount = 0
local treeNodesSample = {}
local sampleLimit = 10

if build.tree and build.tree.allocNodes then
    for nodeId, node in pairs(build.tree.allocNodes) do
        treeNodeCount = treeNodeCount + 1
        if treeNodeCount <= sampleLimit then
            table.insert(treeNodesSample, tostring(nodeId))
        end
    end
end

-- Get spec from build
local specNodeCount = 0
local specNodesSample = {}

if build.spec and build.spec.allocNodes then
    for nodeId, _ in pairs(build.spec.allocNodes) do
        specNodeCount = specNodeCount + 1
        if specNodeCount <= sampleLimit then
            table.insert(specNodesSample, tostring(nodeId))
        end
    end
end

-- Build statistics object
local stats = {
    -- DPS metrics
    totalDPS = safeGet(output, "TotalDPS"),
    combinedDPS = safeGet(output, "CombinedDPS"),
    totalDotDPS = safeGet(output, "TotalDotDPS"),
    fullDPS = safeGet(output, "FullDPS"),
    averageDamage = safeGet(output, "AverageDamage"),
    speed = safeGet(output, "Speed"),
    hitChance = safeGet(output, "AccuracyHitChance"),
    critChance = safeGet(output, "CritChance"),

    -- Defensive stats
    totalEHP = safeGet(output, "TotalEHP"),
    life = safeGet(output, "Life"),
    energyShield = safeGet(output, "EnergyShield"),
    armour = safeGet(output, "Armour"),
    evasion = safeGet(output, "Evasion"),
    blockChance = safeGet(output, "BlockChance"),

    -- Resistances
    fireRes = safeGet(output, "FireResist"),
    coldRes = safeGet(output, "ColdResist"),
    lightningRes = safeGet(output, "LightningResist"),
    chaosRes = safeGet(output, "ChaosResist"),

    -- Attributes
    strength = safeGet(output, "Str"),
    dexterity = safeGet(output, "Dex"),
    intelligence = safeGet(output, "Int"),
}

-- Add debug info about tree
local debugInfo = {
    treeNodeCount = treeNodeCount,
    treeNodesSample = table.concat(treeNodesSample, ","),
    specNodeCount = specNodeCount,
    specNodesSample = table.concat(specNodesSample, ","),
    hasTree = (build.tree ~= nil),
    hasSpec = (build.spec ~= nil),
    hasTreeAllocNodes = (build.tree and build.tree.allocNodes ~= nil),
    hasSpecAllocNodes = (build.spec and build.spec.allocNodes ~= nil),
}

-- Simple JSON encoder
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

-- Output JSON result with debug info
local result = {
    success = true,
    stats = stats,
    debug = debugInfo
}

print(encodeJSON(result))
