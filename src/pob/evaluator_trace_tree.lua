-- Advanced Debug Evaluator - Trace Tree Loading Process
-- This script adds debug hooks to trace exactly what happens during tree loading

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

-- Parse XML to see what Tree sections exist
local xmlSectionInfo = {}
-- Simple pattern matching to find Tree and Spec elements
for elem in xmlContent:gmatch('<([^%s/>]+)[^>]*>') do
    if elem == "Tree" or elem == "Spec" or elem == "Build" or elem == "Skills" or elem == "Items" then
        table.insert(xmlSectionInfo, elem)
    end
end

-- Count nodes in XML
local xmlNodesAttr = xmlContent:match('<Spec[^>]*nodes="([^"]+)"')
local xmlNodeCount = 0
if xmlNodesAttr then
    for _ in xmlNodesAttr:gmatch('[^,]+') do
        xmlNodeCount = xmlNodeCount + 1
    end
end

-- Load HeadlessWrapper
local headless_success, headless_err = pcall(function()
    dofile("HeadlessWrapper.lua")
end)

if not headless_success then
    io.stderr:write('{"success":false,"error":"Failed to load HeadlessWrapper: ' .. tostring(headless_err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

-- Load the build
local success, err = pcall(function()
    loadBuildFromXML(xmlContent, "TestBuild")
end)

if not success then
    io.stderr:write('{"success":false,"error":"Failed to load build: ' .. tostring(err):gsub('"', '\\"') .. '"}\n')
    os.exit(1)
end

-- Give it extra frames to initialize
for i = 1, 10 do
    runCallback("OnFrame")
end

-- Force calculation
if build and build.calcsTab and build.calcsTab.BuildOutput then
    build.buildFlag = true
    build.calcsTab:BuildOutput()
end

runCallback("OnFrame")

-- Comprehensive build state inspection
local buildInfo = {
    buildExists = (build ~= nil),
    hasTree = (build and build.tree ~= nil),
    hasSpec = (build and build.spec ~= nil),
    hasTreeTab = (build and build.treeTab ~= nil),
    hasCalcsTab = (build and build.calcsTab ~= nil),
    hasXmlSectionList = (build and build.xmlSectionList ~= nil),
}

-- Count xmlSectionList
if build and build.xmlSectionList then
    buildInfo.xmlSectionCount = #build.xmlSectionList
    local sectionNames = {}
    for i, node in ipairs(build.xmlSectionList) do
        if type(node) == "table" and node.elem then
            table.insert(sectionNames, node.elem)
        end
    end
    buildInfo.xmlSections = table.concat(sectionNames, ",")
end

-- Check tree.allocNodes
if build and build.tree and build.tree.allocNodes then
    local count = 0
    local sample = {}
    for nodeId, node in pairs(build.tree.allocNodes) do
        count = count + 1
        if count <= 10 then
            table.insert(sample, tostring(nodeId))
        end
    end
    buildInfo.treeAllocNodesCount = count
    buildInfo.treeAllocNodesSample = table.concat(sample, ",")
else
    buildInfo.treeAllocNodesCount = 0
    buildInfo.treeAllocNodesSample = ""
end

-- Check spec.allocNodes
if build and build.spec and build.spec.allocNodes then
    local count = 0
    local sample = {}
    for nodeId, _ in pairs(build.spec.allocNodes) do
        count = count + 1
        if count <= 10 then
            table.insert(sample, tostring(nodeId))
        end
    end
    buildInfo.specAllocNodesCount = count
    buildInfo.specAllocNodesSample = table.concat(sample, ",")
else
    buildInfo.specAllocNodesCount = 0
    buildInfo.specAllocNodesSample = ""
end

-- Check spec.nodes (might be different from allocNodes)
if build and build.spec and build.spec.nodes then
    buildInfo.specNodesCount = #build.spec.nodes
    local sample = {}
    for i = 1, math.min(10, #build.spec.nodes) do
        table.insert(sample, tostring(build.spec.nodes[i]))
    end
    buildInfo.specNodesSample = table.concat(sample, ",")
else
    buildInfo.specNodesCount = 0
    buildInfo.specNodesSample = ""
end

-- Check treeTab state
if build and build.treeTab then
    buildInfo.hasTreeTabSpec = (build.treeTab.spec ~= nil)
    if build.treeTab.spec then
        buildInfo.treeTabSpecNodes = (build.treeTab.spec.nodes and #build.treeTab.spec.nodes or 0)
    end
    -- Check specList
    if build.treeTab.specList then
        buildInfo.specListCount = #build.treeTab.specList
        if #build.treeTab.specList > 0 and build.treeTab.specList[1] then
            local spec1 = build.treeTab.specList[1]
            buildInfo.spec1Exists = true
            buildInfo.spec1HasAllocNodes = (spec1.allocNodes ~= nil)
            if spec1.allocNodes then
                local count = 0
                for _ in pairs(spec1.allocNodes) do
                    count = count + 1
                end
                buildInfo.spec1AllocNodesCount = count
            end
        end
    end
end

-- Get stats
local stats = {}
if build and build.calcsTab and build.calcsTab.mainOutput then
    local output = build.calcsTab.mainOutput
    stats.combinedDPS = output.CombinedDPS or 0
    stats.life = output.Life or 0
else
    stats.combinedDPS = 0
    stats.life = 0
end

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

-- Output comprehensive result
local result = {
    success = true,
    stats = stats,
    xmlInfo = {
        sectionsFound = table.concat(xmlSectionInfo, ","),
        nodesInXML = xmlNodeCount,
    },
    buildInfo = buildInfo,
}

print(encodeJSON(result))
