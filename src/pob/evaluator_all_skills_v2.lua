-- PoB Build Evaluator - All Skills Version 2
-- This version also sets calcsTab.input.skill_number to select socket group
-- Usage: luajit evaluator_all_skills_v2.lua <path_to_build_xml>

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

local headless_success, headless_err = pcall(function()
    dofile("HeadlessWrapper.lua")
end)

if not headless_success then
    io.stderr:write('{"success":false,"error":"Failed to load HeadlessWrapper: ' .. tostring(headless_err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

if not loadBuildFromXML or not build then
    io.stderr:write('{"success":false,"error":"loadBuildFromXML or build not available"}\n')
    os.exit(1)
end

local success, err = pcall(function()
    loadBuildFromXML(xmlContent, "EvaluatedBuild")
end)

if not success then
    io.stderr:write('{"success":false,"error":"Failed to load build: ' .. tostring(err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

for i = 1, 3 do
    runCallback("OnFrame")
end

local function safeGet(output, key, default)
    local value = output[key]
    if value == nil or type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then
        return default or 0
    end
    return math.floor(value * 100 + 0.5) / 100
end

local function getSkillName(socketGroup, skillIndex)
    if not socketGroup.displaySkillListCalcs then return "Unknown" end
    local skill = socketGroup.displaySkillListCalcs[skillIndex]
    if not skill then return "Unknown" end
    if skill.activeEffect and skill.activeEffect.grantedEffect then
        return skill.activeEffect.grantedEffect.name or "Unknown"
    end
    return "Unknown"
end

local allSkills = {}
local maxDPS = 0
local bestSkill = nil

if build.skillsTab and build.skillsTab.socketGroupList and build.calcsTab then
    local socketGroups = build.skillsTab.socketGroupList

    for groupIndex, socketGroup in ipairs(socketGroups) do
        if socketGroup.enabled and socketGroup.displaySkillListCalcs then
            local numSkills = #socketGroup.displaySkillListCalcs

            for skillIndex = 1, numSkills do
                local skillName = getSkillName(socketGroup, skillIndex)

                -- Set this socket group as active in calcsTab
                if build.calcsTab.input then
                    build.calcsTab.input.skill_number = groupIndex
                end

                -- Set this skill as the main skill for this group
                socketGroup.mainActiveSkillCalcs = skillIndex

                -- Trigger calculation
                local calc_success, calc_err = pcall(function()
                    build.buildFlag = true
                    build.calcsTab:BuildOutput()
                end)

                if calc_success and build.calcsTab.mainOutput then
                    local output = build.calcsTab.mainOutput

                    local skillStats = {
                        socketGroup = groupIndex,
                        skillIndex = skillIndex,
                        skillName = skillName,
                        slot = socketGroup.slot or "None",
                        combinedDPS = safeGet(output, "CombinedDPS"),
                        totalDPS = safeGet(output, "TotalDPS"),
                        totalDotDPS = safeGet(output, "TotalDotDPS"),
                        life = safeGet(output, "Life"),
                        energyShield = safeGet(output, "EnergyShield"),
                        totalEHP = safeGet(output, "TotalEHP"),
                    }

                    table.insert(allSkills, skillStats)

                    if skillStats.combinedDPS > maxDPS then
                        maxDPS = skillStats.combinedDPS
                        bestSkill = skillStats
                    end
                end
            end
        end
    end
end

if #allSkills == 0 then
    io.stderr:write('{"success":false,"error":"No skills found or calculated"}\n')
    os.exit(1)
end

local result = {
    success = true,
    stats = {
        combinedDPS = bestSkill.combinedDPS,
        totalDPS = bestSkill.totalDPS,
        totalDotDPS = bestSkill.totalDotDPS,
        life = bestSkill.life,
        energyShield = bestSkill.energyShield,
        totalEHP = bestSkill.totalEHP,
        mainSkillName = bestSkill.skillName,
        mainSkillSlot = bestSkill.slot,
    },
    allSkills = allSkills,
    numSkillsCalculated = #allSkills,
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
            local isArray = true
            local maxIndex = 0
            for k, v in pairs(val) do
                if type(k) ~= "number" or k < 1 or k ~= math.floor(k) then
                    isArray = false
                    break
                end
                maxIndex = math.max(maxIndex, k)
            end
            if isArray and maxIndex > 0 then
                local parts = {}
                for i = 1, maxIndex do
                    table.insert(parts, encodeValue(val[i]))
                end
                return "[" .. table.concat(parts, ",") .. "]"
            else
                local parts = {}
                for k, v in pairs(val) do
                    table.insert(parts, '"' .. tostring(k) .. '":' .. encodeValue(v))
                end
                return "{" .. table.concat(parts, ",") .. "}"
            end
        else
            return "null"
        end
    end
    return encodeValue(obj)
end

print(encodeJSON(result))
