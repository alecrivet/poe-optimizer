-- Debug PoB Build Evaluator - outputs ALL available stats
-- This script loads a Path of Building build from XML and outputs ALL statistics as JSON

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"

local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

local buildXMLPath = arg[1]

if not buildXMLPath then
    io.stderr:write("No build XML file specified\n")
    os.exit(1)
end

local file = io.open(buildXMLPath, "r")
if not file then
    io.stderr:write("Cannot open file: " .. buildXMLPath .. "\n")
    os.exit(1)
end
local xmlContent = file:read("*all")
file:close()

-- Load HeadlessWrapper
dofile("HeadlessWrapper.lua")

-- Load the build
loadBuildFromXML(xmlContent, "DebugBuild")

-- Run calculation frames
for i = 1, 5 do
    runCallback("OnFrame")
end

-- Get output
local output = build and build.calcsTab and build.calcsTab.mainOutput

if not output then
    print("ERROR: No output available")
    os.exit(1)
end

-- Print ALL keys in output
print("\n=== ALL AVAILABLE STATS IN mainOutput ===\n")

-- Collect and sort keys
local keys = {}
for k, v in pairs(output) do
    table.insert(keys, k)
end
table.sort(keys)

-- Print each stat
for _, key in ipairs(keys) do
    local value = output[key]
    local valueStr = tostring(value)

    -- Format numbers nicely
    if type(value) == "number" then
        if value ~= value then
            valueStr = "NaN"
        elseif value == math.huge then
            valueStr = "Infinity"
        elseif value == -math.huge then
            valueStr = "-Infinity"
        elseif value > 1000000 then
            valueStr = string.format("%.2e (%.2f)", value, value)
        else
            valueStr = string.format("%.2f", value)
        end
    end

    print(string.format("%-40s = %s", key, valueStr))
end

print("\n=== DPS-RELATED STATS ===\n")
local dpsKeys = {}
for k, v in pairs(output) do
    if string.find(string.lower(k), "dps") or
       string.find(string.lower(k), "damage") or
       string.find(string.lower(k), "average") then
        table.insert(dpsKeys, k)
    end
end
table.sort(dpsKeys)

for _, key in ipairs(dpsKeys) do
    local value = output[key]
    if type(value) == "number" then
        print(string.format("%-40s = %.2f", key, value))
    else
        print(string.format("%-40s = %s", key, tostring(value)))
    end
end

-- Print SkillDPS table if it exists
if output.SkillDPS and type(output.SkillDPS) == "table" then
    print("\n=== SKILL DPS BREAKDOWN ===\n")
    for skillIndex, dps in pairs(output.SkillDPS) do
        print(string.format("Skill %s: %.2f DPS", tostring(skillIndex), dps))
    end
end
