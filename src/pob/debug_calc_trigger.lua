-- Debug script to investigate calculation triggering
-- Run from PathOfBuilding/src directory

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"

-- Add LuaRocks path for binary modules (like lua-utf8)
local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

local buildXMLPath = arg[1]
if not buildXMLPath then
    print("ERROR: No build XML file specified")
    os.exit(1)
end

local file = io.open(buildXMLPath, "r")
if not file then
    print("ERROR: Cannot open file: " .. buildXMLPath)
    os.exit(1)
end
local xmlContent = file:read("*all")
file:close()

-- Load HeadlessWrapper
local success, err = pcall(function()
    dofile("HeadlessWrapper.lua")
end)

if not success then
    print("ERROR loading HeadlessWrapper:", err)
    os.exit(1)
end

if not loadBuildFromXML then
    print("ERROR: loadBuildFromXML not available")
    os.exit(1)
end

if not build then
    print("ERROR: build object not available")
    os.exit(1)
end

-- Load build
local load_success, load_err = pcall(function()
    loadBuildFromXML(xmlContent, "DebugBuild")
end)

if not load_success then
    print("ERROR loading build:", load_err)
    os.exit(1)
end

print("\n=== Initial State (after loadBuildFromXML) ===")
print("build exists:", build ~= nil)
print("build.buildFlag:", build and build.buildFlag or "nil")
print("build.calcsTab exists:", build and build.calcsTab ~= nil)
print("build.skillsTab exists:", build and build.skillsTab ~= nil)

if build and build.skillsTab then
    print("build.skillsTab.socketGroupList:", build.skillsTab.socketGroupList ~= nil)
    if build.skillsTab.socketGroupList then
        print("  Number of socket groups:", #build.skillsTab.socketGroupList)
    end
end

-- Run a few OnFrame cycles
print("\n=== Running 3 OnFrame() cycles ===")
for i = 1, 3 do
    print("Frame", i)
    runCallback("OnFrame")
    print("  buildFlag:", build.buildFlag or "false")
end

-- Manually trigger BuildOutput
print("\n=== Manually triggering BuildOutput() ===")
if build and build.calcsTab and build.calcsTab.BuildOutput then
    build.buildFlag = true
    print("Set buildFlag = true")

    local success, err = pcall(function()
        build.calcsTab:BuildOutput()
    end)

    if success then
        print("✓ BuildOutput() called successfully")
    else
        print("✗ BuildOutput() failed:", err)
    end
else
    print("✗ BuildOutput not available")
end

-- Run one more OnFrame
print("\n=== Running 1 more OnFrame() ===")
runCallback("OnFrame")

-- Check output
print("\n=== Checking Output ===")
if build and build.calcsTab then
    print("calcsTab.mainOutput exists:", build.calcsTab.mainOutput ~= nil)
    print("calcsTab.mainEnv exists:", build.calcsTab.mainEnv ~= nil)

    if build.calcsTab.mainOutput then
        print("\nMain Output Stats:")
        print("  CombinedDPS:", build.calcsTab.mainOutput.CombinedDPS or "nil")
        print("  Life:", build.calcsTab.mainOutput.Life or "nil")
        print("  TotalEHP:", build.calcsTab.mainOutput.TotalEHP or "nil")
    end
end

-- Check skill groups
print("\n=== Checking Skill Groups ===")
if build and build.skillsTab and build.skillsTab.socketGroupList then
    local groups = build.skillsTab.socketGroupList
    print("Number of socket groups:", #groups)

    for i, group in ipairs(groups) do
        print(string.format("\nGroup %d:", i))
        print("  label:", group.label or "nil")
        print("  enabled:", group.enabled or false)
        print("  displaySkillList exists:", group.displaySkillList ~= nil)
        print("  displaySkillListCalcs exists:", group.displaySkillListCalcs ~= nil)

        if group.displaySkillListCalcs and #group.displaySkillListCalcs > 0 then
            print("  Number of skills in displaySkillListCalcs:", #group.displaySkillListCalcs)
            local skill = group.displaySkillListCalcs[1]
            if skill and skill.activeEffect then
                print("    First skill activeEffect exists")
                if skill.activeEffect.grantedEffect then
                    print("    Skill name:", skill.activeEffect.grantedEffect.name or "nil")
                end
            end
        end
    end
end

print("\n=== Done ===")
