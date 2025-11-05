-- Evaluator with Manual Tree Loading Workaround
-- Since TreeTab:Load() isn't being called automatically in headless mode,
-- we manually load the tree after initialization

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
dofile("HeadlessWrapper.lua")

-- Load the build
loadBuildFromXML(xmlContent, "TestBuild")

-- Give it frames to initialize
for i = 1, 5 do
    runCallback("OnFrame")
end

-- WORKAROUND: Manually load tree if specList is empty
if build and build.treeTab and build.treeTab.specList and #build.treeTab.specList == 0 then
    -- Parse XML to find Tree section
    local xml = require("xml")
    local parsed = xml.ParseXML(xmlContent)

    if parsed and parsed[1] then
        -- Find Tree element
        for _, node in ipairs(parsed[1]) do
            if type(node) == "table" and node.elem == "Tree" then
                -- Manually call TreeTab:Load()
                local success, err = pcall(function()
                    build.treeTab:Load(node, nil)
                end)

                if not success then
                    io.stderr:write('{"success":false,"error":"Manual tree load failed: ' .. tostring(err):gsub('"', '\\"') .. '"}\n')
                    os.exit(1)
                end

                -- Call PostLoad
                if build.treeTab.PostLoad then
                    build.treeTab:PostLoad()
                end

                break
            end
        end
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
    io.stderr:write('{"success":false,"error":"Build calculations failed - no output available"}\n')
    os.exit(1)
end

-- Helper function
local function safeGet(output, key, default)
    local value = output[key]
    if value == nil or type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then
        return default or 0
    end
    return math.floor(value * 100 + 0.5) / 100
end

-- Build statistics
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

-- Output result
local result = {
    success = true,
    stats = stats
}

print(encodeJSON(result))
