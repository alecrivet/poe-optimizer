-- Debug PoB Build Structure - explore the entire build object

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
for i = 1, 10 do  -- More frames to ensure calculations complete
    runCallback("OnFrame")
end

-- Explore build structure
print("\n=== BUILD STRUCTURE ===\n")

if build then
    print("build object exists")

    if build.calcsTab then
        print("\nbuild.calcsTab exists")

        -- Check for active skill
        if build.calcsTab.mainActiveSkill then
            print("  Active skill index:", build.calcsTab.mainActiveSkill)
        end

        if build.calcsTab.mainActiveSkillCalcs then
            print("  mainActiveSkillCalcs exists")
        end

        -- List all skills
        if build.skillsTab and build.skillsTab.skillList then
            print("\n=== SKILLS ===")
            for i, skill in ipairs(build.skillsTab.skillList) do
                print(string.format("Skill %d:", i))
                if skill.activeEffect and skill.activeEffect.grantedEffect then
                    print("  Name:", skill.activeEffect.grantedEffect.name)
                end

                -- Check if this skill has DPS output
                if build.calcsTab and build.calcsTab.mainOutput and build.calcsTab.mainOutput.SkillDPS then
                    local skillDPS = build.calcsTab.mainOutput.SkillDPS[i]
                    if skillDPS then
                        print(string.format("  DPS: %.2f", skillDPS))
                    end
                end
            end
        end

        -- Check mainOutput
        if build.calcsTab.mainOutput then
            print("\n=== MAIN OUTPUT KEY DPS STATS ===")
            local output = build.calcsTab.mainOutput

            -- Print all DPS-related stats with large values
            for k, v in pairs(output) do
                if type(v) == "number" and v > 100000 then
                    print(string.format("%-40s = %.2f", k, v))
                end
            end
        end
    end
end
