-- Debug script to explore per-skill output data
-- Check if socket groups have their own output data

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"
local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

local buildXMLPath = arg[1]
local file = io.open(buildXMLPath, "r")
local xmlContent = file:read("*all")
file:close()

dofile("HeadlessWrapper.lua")
loadBuildFromXML(xmlContent, "DebugBuild")

for i = 1, 3 do
    runCallback("OnFrame")
end

build.buildFlag = true
build.calcsTab:BuildOutput()

print("\n=== Exploring Socket Group Output ===")

if build.skillsTab and build.skillsTab.socketGroupList then
    for groupIndex, socketGroup in ipairs(build.skillsTab.socketGroupList) do
        if socketGroup.enabled then
            print(string.format("\nGroup %d (%s):", groupIndex, socketGroup.slot or "None"))

            -- Check for activeSkill output
            if socketGroup.activeSkill then
                print("  activeSkill exists:", socketGroup.activeSkill ~= nil)
            end

            -- Check displaySkillListCalcs
            if socketGroup.displaySkillListCalcs then
                print("  displaySkillListCalcs count:", #socketGroup.displaySkillListCalcs)

                for skillIndex, skill in ipairs(socketGroup.displaySkillListCalcs) do
                    if skill.activeEffect and skill.activeEffect.grantedEffect then
                        print(string.format("    Skill %d: %s", skillIndex, skill.activeEffect.grantedEffect.name))
                    end

                    -- Check if skill has output
                    if skill.output then
                        print("      HAS OUTPUT!")
                        if skill.output.CombinedDPS then
                            print(string.format("        CombinedDPS: %.2f", skill.output.CombinedDPS))
                        end
                    end

                    -- Check activeEffect for output
                    if skill.activeEffect and skill.activeEffect.output then
                        print("      activeEffect HAS OUTPUT!")
                        if skill.activeEffect.output.CombinedDPS then
                            print(string.format("        CombinedDPS: %.2f", skill.activeEffect.output.CombinedDPS))
                        end
                    end
                end
            end
        end
    end
end

print("\n=== Checking calcsTab.calcsOutput vs mainOutput ===")
if build.calcsTab.calcsOutput and build.calcsTab.mainOutput then
    print("mainOutput.CombinedDPS:", build.calcsTab.mainOutput.CombinedDPS)
    print("calcsOutput.CombinedDPS:", build.calcsTab.calcsOutput.CombinedDPS)
end

print("\n=== Done ===")
