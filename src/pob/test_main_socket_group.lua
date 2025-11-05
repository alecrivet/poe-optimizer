-- Test: Does setting mainSocketGroup affect calculations?
-- Run from PathOfBuilding/src directory

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"
local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

dofile("HeadlessWrapper.lua")

local buildXMLPath = "../../examples/build2.xml"
local file = io.open(buildXMLPath, "r")
local xml = file:read("*all")
file:close()

print("\n" .. string.rep("=", 70))
print("Testing mainSocketGroup Selection")
print(string.rep("=", 70))

loadBuildFromXML(xml, "TestBuild")

for i = 1, 5 do
    runCallback("OnFrame")
end

-- Get initial state
print("\n1. Current configuration:")
print("   mainSocketGroup:", build.mainSocketGroup)
print("   Socket groups:")

if build.skillsTab and build.skillsTab.socketGroupList then
    for i, group in ipairs(build.skillsTab.socketGroupList) do
        local label = group.label or "no label"
        local slot = group.slot or "no slot"
        local enabled = group.enabled and "enabled" or "disabled"

        print(string.format("     Group %d: %s (%s, %s)", i, slot, label, enabled))

        if group.displaySkillListCalcs then
            for j, skill in ipairs(group.displaySkillListCalcs) do
                if skill.activeEffect and skill.activeEffect.grantedEffect then
                    print(string.format("       - %s", skill.activeEffect.grantedEffect.name))
                end
            end
        end
    end
end

-- Test each socket group
print("\n2. Testing DPS for each socket group:")

for groupNum = 1, 6 do
    -- Set mainSocketGroup
    build.mainSocketGroup = groupNum

    -- Trigger calculation
    build.buildFlag = true
    if build.calcsTab and build.calcsTab.BuildOutput then
        build.calcsTab:BuildOutput()
    end

    runCallback("OnFrame")

    -- Get results
    if build.calcsTab and build.calcsTab.mainOutput then
        local output = build.calcsTab.mainOutput
        local group = build.skillsTab.socketGroupList[groupNum]
        local slot = group and group.slot or "unknown"

        print(string.format("   Group %d (%s):", groupNum, slot))
        print(string.format("     CombinedDPS: %.0f", output.CombinedDPS or 0))
        print(string.format("     TotalDPS: %.0f", output.TotalDPS or 0))
        print(string.format("     FullDPS: %.0f", output.FullDPS or 0))
    end
end

print("\n3. Expected values from XML:")
print("   CombinedDPS: 3,163,831")
print("   TotalDPS: 1,822,582")
print("   FullDPS: 0")

print("\n" .. string.rep("=", 70))
print("Conclusion: If all groups show same DPS, mainSocketGroup isn't working")
print(string.rep("=", 70))
