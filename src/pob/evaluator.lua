-- PoB Build Evaluator
-- This script loads a Path of Building build from XML and outputs statistics as JSON
-- Usage: luajit evaluator.lua <path_to_build_xml>
-- Must be run from PathOfBuilding/src directory (Python caller handles this)

-- Add PoB's runtime Lua modules to the package path
-- This allows loading xml.lua, dkjson.lua, sha1/init.lua, etc. from PathOfBuilding/runtime/lua/
package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"

-- Add LuaRocks path for binary modules (like lua-utf8)
-- Try to use luarocks-installed modules from user's home directory
local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

-- Parse command-line arguments
local buildXMLPath = arg[1]

if not buildXMLPath then
    io.stderr:write('{"success":false,"error":"No build XML file specified"}\n')
    os.exit(1)
end

-- Check if file exists and read XML content
local file = io.open(buildXMLPath, "r")
if not file then
    io.stderr:write('{"success":false,"error":"Cannot open file: ' .. buildXMLPath .. '"}\n')
    os.exit(1)
end
local xmlContent = file:read("*all")
file:close()

-- Load HeadlessWrapper (which initializes PoB)
local headless_success, headless_err = pcall(function()
    dofile("HeadlessWrapper.lua")
end)

if not headless_success then
    io.stderr:write('{"success":false,"error":"Failed to load HeadlessWrapper: ' .. tostring(headless_err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

-- Check if required functions are available
if not loadBuildFromXML then
    io.stderr:write('{"success":false,"error":"loadBuildFromXML function not available after loading HeadlessWrapper"}\n')
    os.exit(1)
end

if not build then
    io.stderr:write('{"success":false,"error":"build object not available after loading HeadlessWrapper"}\n')
    os.exit(1)
end

-- Try to load the build from XML
local success, err = pcall(function()
    loadBuildFromXML(xmlContent, "EvaluatedBuild")
end)

if not success then
    io.stderr:write('{"success":false,"error":"Failed to load build: ' .. tostring(err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

-- Give PoB additional frames to complete calculations
for i = 1, 5 do
    runCallback("OnFrame")
end

-- Extract statistics from the build
local output = build and build.calcsTab and build.calcsTab.mainOutput
if not output then
    io.stderr:write('{"success":false,"error":"Build calculations failed - no output available"}\n')
    os.exit(1)
end

-- Helper function to safely get and format output values
local function safeGet(output, key, default)
    local value = output[key]
    if value == nil then
        return default or 0
    end
    -- Handle NaN and Infinity
    if type(value) ~= "number" then
        return default or 0
    end
    if value ~= value then -- NaN check
        return default or 0
    end
    if value == math.huge or value == -math.huge then
        return default or 0
    end
    -- Round to avoid floating point precision issues in JSON
    return math.floor(value * 100 + 0.5) / 100
end

-- Build statistics object
local stats = {
    -- DPS metrics
    totalDPS = safeGet(output, "TotalDPS"),
    fullDPS = safeGet(output, "FullDPS"),

    -- Defensive stats
    totalEHP = safeGet(output, "TotalEHP"),
    life = safeGet(output, "Life"),
    energyShield = safeGet(output, "EnergyShield"),

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

-- Simple JSON encoder (avoid external dependencies)
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

-- Output JSON result
local result = {
    success = true,
    stats = stats
}

print(encodeJSON(result))
