-- Try to force PoB to properly initialize skills

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
loadBuildFromXML(xmlContent, "TestBuild")

-- Try different methods to force skill processing
for i = 1, 30 do
    runCallback("OnFrame")
end

-- Try to manually trigger skill list building
if build and build.skillsTab then
    print("Attempting to force skill list creation...")

    -- Try calling various methods that might exist
    if build.skillsTab.BuildSkillList then
        print("  Calling BuildSkillList()")
        build.skillsTab:BuildSkillList()
    end

    if build.skillsTab.Build then
        print("  Calling Build()")
        build.skillsTab:Build()
    end

    -- Force more frames
    for i = 1, 10 do
        runCallback("OnFrame")
    end

    -- Check if it worked
    if build.skillsTab.skillList then
        print(string.format("SUCCESS: skillList now has %d skills", #build.skillsTab.skillList))
    else
        print("FAILED: skillList is still nil")
    end
end

-- Check main output
if build and build.calcsTab and build.calcsTab.mainOutput then
    local output = build.calcsTab.mainOutput
    print(string.format("\nTotalDPS: %.2f", output.TotalDPS or 0))
    print(string.format("CombinedDPS: %.2f", output.CombinedDPS or 0))
end
