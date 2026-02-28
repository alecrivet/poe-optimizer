-- Debug script to examine all skills and their DPS

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
    io.stderr:write("Cannot open file\n")
    os.exit(1)
end
local xmlContent = file:read("*all")
file:close()

dofile("HeadlessWrapper.lua")
loadBuildFromXML(xmlContent, "DebugBuild")

-- Run more frames to ensure calculations complete
for i = 1, 20 do
    runCallback("OnFrame")
end

print("\n=== BUILD STRUCTURE ===\n")

if not build then
    print("ERROR: build object not available")
    os.exit(1)
end

print("build exists:", build ~= nil)

-- Check what tabs exist
local tabs = {"skillsTab", "itemsTab", "calcsTab", "treeTab", "configTab", "notesTab"}
for _, tabName in ipairs(tabs) do
    if build[tabName] then
        print(string.format("  build.%s exists", tabName))

        if tabName == "skillsTab" then
            if build.skillsTab.skillList then
                print(string.format("    skillList exists with %d skills", #build.skillsTab.skillList))
            else
                print("    skillList is nil")
            end

            if build.skillsTab.activeSkill then
                print(string.format("    activeSkill = %s", tostring(build.skillsTab.activeSkill)))
            end
        end
    else
        print(string.format("  build.%s is nil", tabName))
    end
end

print("\n=== INVESTIGATING SKILLS ===\n")

if not build.skillsTab then
    print("ERROR: build.skillsTab not available")
    os.exit(1)
end

print("Number of skills:", build.skillsTab.skillList and #build.skillsTab.skillList or 0)

if build.skillsTab.skillList then
    for i, skill in ipairs(build.skillsTab.skillList) do
        print(string.format("\n--- Skill %d ---", i))

        -- Try to get skill name
        if skill.activeEffect and skill.activeEffect.grantedEffect then
            print("  Name:", skill.activeEffect.grantedEffect.name)
        elseif skill.activeGem and skill.activeGem.nameSpec then
            print("  Name:", skill.activeGem.nameSpec)
        else
            print("  Name: Unknown")
        end

        -- Check if this is the active skill
        if build.skillsTab.activeSkillSpec == skill.skillCfg or i == build.skillsTab.activeSkill then
            print("  *** ACTIVE SKILL ***")
        end
    end
end

-- Force recalculation with each skill as active
if build.skillsTab.skillList and build.calcsTab then
    print("\n\n=== CALCULATING DPS FOR EACH SKILL ===\n")

    for i, skill in ipairs(build.skillsTab.skillList) do
        -- Try to set this as active skill
        if build.skillsTab.SetActiveSkill then
            build.skillsTab:SetActiveSkill(i, false)
        elseif build.skillsTab.SelectSkill then
            build.skillsTab:SelectSkill(i)
        else
            build.skillsTab.activeSkill = i
        end

        -- Force recalculation
        for f = 1, 5 do
            runCallback("OnFrame")
        end

        local output = build.calcsTab.mainOutput
        if output then
            local name = "Unknown"
            if skill.activeEffect and skill.activeEffect.grantedEffect then
                name = skill.activeEffect.grantedEffect.name
            end

            local totalDPS = output.TotalDPS or 0
            local combinedDPS = output.CombinedDPS or 0

            if totalDPS > 0 or combinedDPS > 0 then
                print(string.format("Skill %d (%s):", i, name))
                print(string.format("  TotalDPS:    %15,.2f", totalDPS))
                print(string.format("  CombinedDPS: %15,.2f", combinedDPS))
            end
        end
    end
end
