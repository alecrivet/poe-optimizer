-- Quick validation test: Does PostLoad fix skill loading?
-- Run from PathOfBuilding/src directory

package.path = package.path .. ";../runtime/lua/?.lua;../runtime/lua/?/init.lua"

local home = os.getenv("HOME") or ""
if home ~= "" then
    package.cpath = package.cpath .. ";" .. home .. "/.luarocks/lib/lua/5.1/?.so"
end

-- Load HeadlessWrapper
dofile("HeadlessWrapper.lua")

-- Load build2 XML
local buildXMLPath = "../../examples/build2.xml"
local file = io.open(buildXMLPath, "r")
if not file then
    print("ERROR: Cannot open " .. buildXMLPath)
    os.exit(1)
end
local xml = file:read("*all")
file:close()

print("=" .. string.rep("=", 69))
print("Testing PostLoad Fix for HeadlessWrapper")
print("=" .. string.rep("=", 69))

-- Load build normally
print("\n1. Loading build via HeadlessWrapper...")
loadBuildFromXML(xml, "TestBuild")

-- Give it some frames
for i = 1, 5 do
    runCallback("OnFrame")
end

-- Check initial state
print("\n2. Initial state (after loadBuildFromXML):")
print("   build exists:", build ~= nil)
print("   skillsTab exists:", build and build.skillsTab ~= nil)
print("   calcsTab exists:", build and build.calcsTab ~= nil)

if build and build.skillsTab then
    print("   socketGroupList exists:", build.skillsTab.socketGroupList ~= nil)
    if build.skillsTab.socketGroupList then
        print("   socketGroupList count:", #build.skillsTab.socketGroupList)
    end
end

-- Trigger initial calculation
print("\n3. Triggering initial BuildOutput...")
if build and build.calcsTab and build.calcsTab.BuildOutput then
    build.buildFlag = true
    build.calcsTab:BuildOutput()

    if build.calcsTab.mainOutput then
        print("   CombinedDPS:", build.calcsTab.mainOutput.CombinedDPS or "nil")
        print("   Life:", build.calcsTab.mainOutput.Life or "nil")
        print("   TotalEHP:", build.calcsTab.mainOutput.TotalEHP or "nil")
    else
        print("   mainOutput is nil!")
    end
end

-- Try calling PostLoad on all tabs
print("\n4. Calling PostLoad on all tabs...")

local postLoadCalled = 0

if build.itemsTab and build.itemsTab.PostLoad then
    print("   Calling itemsTab:PostLoad()...")
    build.itemsTab:PostLoad()
    postLoadCalled = postLoadCalled + 1
end

if build.skillsTab and build.skillsTab.PostLoad then
    print("   Calling skillsTab:PostLoad()...")
    build.skillsTab:PostLoad()
    postLoadCalled = postLoadCalled + 1
end

if build.treeTab and build.treeTab.PostLoad then
    print("   Calling treeTab:PostLoad()...")
    build.treeTab:PostLoad()
    postLoadCalled = postLoadCalled + 1
end

if build.calcsTab and build.calcsTab.PostLoad then
    print("   Calling calcsTab:PostLoad()...")
    build.calcsTab:PostLoad()
    postLoadCalled = postLoadCalled + 1
end

if build.configTab and build.configTab.PostLoad then
    print("   Calling configTab:PostLoad()...")
    build.configTab:PostLoad()
    postLoadCalled = postLoadCalled + 1
end

print("   PostLoad called on " .. postLoadCalled .. " tabs")

-- Give it some frames to process
print("\n5. Running OnFrame cycles...")
for i = 1, 3 do
    runCallback("OnFrame")
end

-- Trigger calculation again
print("\n6. Triggering BuildOutput after PostLoad...")
if build and build.calcsTab and build.calcsTab.BuildOutput then
    build.buildFlag = true
    build.calcsTab:BuildOutput()
end

-- Give one more frame
runCallback("OnFrame")

-- Check final results
print("\n7. Final results:")
if build and build.calcsTab and build.calcsTab.mainOutput then
    local output = build.calcsTab.mainOutput

    print("   CombinedDPS: " .. (output.CombinedDPS or 0))
    print("   TotalDPS: " .. (output.TotalDPS or 0))
    print("   Life: " .. (output.Life or 0))
    print("   TotalEHP: " .. (output.TotalEHP or 0))

    -- Check if we got the correct values
    local combinedDPS = output.CombinedDPS or 0
    local expectedDPS = 3163830  -- Expected from XML
    local tolerance = expectedDPS * 0.01  -- 1% tolerance

    print("\n8. Validation:")
    print("   Expected DPS: ~" .. expectedDPS)
    print("   Actual DPS: " .. combinedDPS)

    if math.abs(combinedDPS - expectedDPS) < tolerance then
        print("\n   ✓ SUCCESS! PostLoad fixed the DPS calculation!")
        print("   ✓ We can build an improved headless wrapper!")
    elseif combinedDPS > 1000000 then
        print("\n   ~ PARTIAL SUCCESS! DPS is closer but not exact")
        print("   ~ May need additional initialization steps")
    else
        print("\n   ✗ FAILED! DPS still incorrect")
        print("   ✗ PostLoad alone isn't enough, need deeper investigation")
    end
else
    print("   ERROR: Cannot access mainOutput")
end

print("\n" .. string.rep("=", 70))
print("Test Complete")
print(string.rep("=", 70))
