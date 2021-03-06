# Copyright (c) 2012 The Khronos Group Inc.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and /or associated documentation files (the "Materials "), to deal in the Materials without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Materials, and to permit persons to whom the Materials are furnished to do so, subject to 
# the following conditions: 
# The above copyright notice and this permission notice shall be included 
# in all copies or substantial portions of the Materials. 
# THE MATERIALS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.

import os
import os.path
import wx
import xml.sax

import Core.Common.FUtils as FUtils
from Core.Gui.FAnimation import *
from Core.Gui.Dialog.FCompareSetupDialog import *
from Core.Gui.Dialog.FComparisonDialog import *
from Core.Gui.Grid.FAssetHandler import *
from Core.Gui.Grid.FImageRenderArea import *
from Core.Gui.Grid.FTextRenderer import *
from Core.Gui.FImageType import *

# used with an FExecutionGrid
class FImageRenderer(FTextRenderer):
    __ANIMATION_FRAME_EXECUTABLE = "./FAnimationViewer.py"
    __CURRENT = 0
    __PREVIOUS = 1
    __BLESSED = 2
    
    def __init__(self, feelingViewerPath, pythonPath, imageWidth, imageHeight, 
                 testProcedure, showBlessed, showPrevious, showCounts = True):
        FTextRenderer.__init__(self)
        self.__feelingViewerPath = feelingViewerPath
        self.__pythonPath = pythonPath
        
        self.__imageWidth = imageWidth
        self.__imageHeight = imageHeight
        self.__showCounts = showCounts
        self.__testProcedure = testProcedure
        self.__showBlessed = showBlessed
        self.__showPrevious = showPrevious
        
        self.__diffCommand = ""
        self.__animateAll = False
        
        self.__renderedAreas = {} # {(row, col) : [FImageRenderArea]}
        self.__animations = {} # {(row, col, id) : ""}
    
    def SetAnimateAll(self, value):
        self.__animateAll = value
    
    def SetDiffCommand(self, diffCommand):
        self.__diffCommand = diffCommand
    
    def SetThumbnailSize(self, width, height):
        self.__imageWidth = width
        self.__imageHeight = height
    
    def SetShowBlessed(self, value):
        self.__showBlessed = value
    
    def SetShowPrevious(self, value):
        self.__showPrevious = value
    
    def __DrawImage(self, image, filename, dc, rect, row, col, type):
        dx = image.GetWidth() - self.__imageWidth
        dy = image.GetHeight() - self.__imageHeight
        
        if ((dx > 0) or (dy > 0)):
            if (dx > dy):
                newWidth = float(self.__imageWidth)
                ratio = newWidth / image.GetWidth()
                newHeight = ratio * image.GetHeight()
            else:
                newHeight = float(self.__imageHeight)
                ratio = newHeight / image.GetHeight()
                newWidth = ratio * image.GetWidth()
            image.Rescale(int(newWidth), int(newHeight))
        
        width, height = image.GetWidth(), image.GetHeight()
        
        if width > rect.width-2:
            width = rect.width-2
            
        if height > rect.height-2:
            height = rect.height-2
        
        offscreenBuffer = wx.EmptyBitmap(width, height)
        imageDC = wx.MemoryDC()
        imageDC.SelectObject(offscreenBuffer)
        
        imageDC.SetBrush(dc.GetBrush())
        imageDC.SetPen(wx.Pen(dc.GetBrush().GetColour()))
        imageDC.DrawRectangle(0, 0, width, height)
        imageDC.DrawBitmap(wx.BitmapFromImage(image), 0, 0, True)
        
        dc.Blit(rect.x + 1, rect.y + 1, width, height, imageDC, 0, 0, wx.COPY, 
                True)
        
        # None if it is a (No Blessed) or (No Preview) image
        if (filename != None):
            self.__renderedAreas[(row, col)].append(FImageRenderArea(
                    rect.x + 1, rect.y + 1, width, height, filename, type))
    
    # lengths of filenames and images could be different if it is an animation 
    # that only needs to display 1 frame
    def __TestAndDraw(self, rect, xOffset, yOffset, images, filenames, grid, 
                      dc, row, col, id, type):
        length = len(images)
        
        newRectWidth = min(rect.width - xOffset, self.__imageWidth)
        newRectHeight = min(rect.height - yOffset, self.__imageHeight)
        if ((newRectWidth > 0) and (newRectHeight > 0)):
            newRect = wx.Rect(rect.x + xOffset, rect.y + yOffset, newRectWidth,
                              newRectHeight)
            
            if (grid.IsRectVisible(newRect)):
                if (length == 1):
                    self.__DrawImage(images[0], filenames, dc, newRect, row, 
                                     col, type)
                else:
                    animation = FAnimation(images, filenames, row, col, 
                            self.__imageWidth, self.__imageHeight, newRect, 
                            self.__renderedAreas, dc.GetBrush().GetColour())
                    animation.Start()
                    grid.AddAnimation(row, col, id, animation)
                    self.__animations[(row, col, id)] = ""
            
            xOffset = xOffset + self.__imageWidth + 10
            yOffset = yOffset + self.__imageHeight + 10
        return (xOffset, yOffset)
    
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        if (self.__renderedAreas.has_key((row, col))):
            self.__renderedAreas.pop((row, col))
            ids = [FImageRenderer.__BLESSED, FImageRenderer.__PREVIOUS, 
                   FImageRenderer.__CURRENT]
            for id in ids:
                if (self.__animations.has_key((row, col, id))):
                    grid.DeleteAnimation(row, col, id)
                    self.__animations.pop((row, col, id))
        
        imageData = grid.GetCellValue(row, col)
        
        # test not yet ran
        if (imageData == None):
            FTextRenderer.Draw(self, grid, attr, dc, rect, row, col, 
                               isSelected)
            return 
        
        if (imageData.GetErrorCount() > 0):
            FTextRenderer.ColorDraw(self, dc, rect, wx.Color(255, 0, 0))
        elif (imageData.GetWarningCount() > 0):
            FTextRenderer.ColorDraw(self, dc, rect, wx.Color(255, 255, 0))
        else:
            FTextRenderer.Draw(self, grid, attr, dc, rect, row, col, 
                                   isSelected)
        
        dc.DestroyClippingRegion()
        dc.SetClippingRect(rect)
        
        self.__renderedAreas[(row, col)] = []
        
        xOffset = 0
        yOffset = 0
        if (self.__showBlessed):
            filenames = imageData.GetBlessedFilenames()
            if ((len(filenames) == 1) or self.__animateAll or isSelected):
                images = imageData.GetBlessedImages()
                if (len(filenames) == 1):
                    filenames = filenames[0]
                    type = FImageType.IMAGE
                else:
                    type = FImageType.ANIMATION
            else:
                images = [imageData.GetBlessedImage(-1),]
                type = FImageType.ANIMATION
            xOffset, dummy = self.__TestAndDraw(rect, xOffset, yOffset, 
                    images, filenames, grid, dc, row, col,
                    FImageRenderer.__BLESSED, type)
        
        if (self.__showPrevious):
            filenames = imageData.GetPreviousFilenames()
            if ((len(filenames) == 1) or self.__animateAll or isSelected):
                images = imageData.GetPreviousImages()
                if (len(filenames) == 1):
                    filenames = filenames[0]
                    type = FImageType.IMAGE
                else:
                    type = FImageType.ANIMATION
            else:
                images = [imageData.GetPreviousImage(-1),]
                type = FImageType.ANIMATION
            xOffset, dummy = self.__TestAndDraw(rect, xOffset, yOffset, 
                    images, filenames, grid, dc, row, col,
                    FImageRenderer.__PREVIOUS, type)
        
        filenames = imageData.GetFilenames()
        if ((len(filenames) == 1) or self.__animateAll or isSelected):
            images = imageData.GetImages()
            if (len(filenames) == 1):
                filenames = filenames[0]
                type = FImageType.IMAGE
            else:
                type = FImageType.ANIMATION
        else:
            images = [imageData.GetImage(-1),]
            type = FImageType.ANIMATION
        self.__TestAndDraw(rect, xOffset, yOffset, images,
                filenames, grid, dc, row, col,
                FImageRenderer.__CURRENT, type)
        
        rect.SetY(rect.y + self.__imageHeight + 1)
        rect.SetHeight(rect.height - self.__imageHeight - 1)
        
        if (self.__showCounts):
            textArray = []
            dataArray = []
            extraArray = []
            textArray.append(str(imageData.GetWarningCount()) + " warnings")
            dataArray.append(imageData.GetLogFilename())
            extraArray.append(FImageType.LOG)
            textArray.append(str(imageData.GetErrorCount()) + " errors")
            dataArray.append(imageData.GetLogFilename())
            extraArray.append(FImageType.LOG)
            
            newY = self.RenderText(grid, attr, dc, rect, row, col, isSelected, 
                    len(textArray), textArray, self.__renderedAreas, dataArray, 
                    extraArray, wx.Color(0, 0, 0))
            
            heightDiff = newY - rect.y
            rect.SetY(newY)
            rect.SetHeight(rect.height - heightDiff) 
        
        dc.DestroyClippingRegion()
    
    def GetBestSize(self, grid, attr, dc, row, col):
        return wx.Size(self.__imageHeight, self.__imageWidth)
    
    def __GetOpenFunc(self, file, type, grid):
        # Should we open an external loader?
        internalLoad = (type == FImageType.ANIMATION)
        if (type == FImageType.IMAGE):
            extension = FUtils.GetExtension(file).lower()
            if (extension == "png"):
                internalLoad = True
                file = [file]

        if internalLoad:
            def Open(e):
                # Open the internal viewer as a separate process.
                args = (["\"" + self.__pythonPath + "\"", 
                        "\"" + FImageRenderer.__ANIMATION_FRAME_EXECUTABLE + 
                        "\""])
                for filename in file:
                    args.append("\"" + filename + "\"")
                os.spawnv(os.P_DETACH, self.__pythonPath, args)
        else:
            def Open(e):
                # Open the default viewer for this file.
                if (os.path.isfile(file)):
                    # XXX: this is windows only
                    os.startfile("\"" + file  + "\"")
                else:
                    FUtils.ShowWarning(grid.GetParent(), "Missing File.")
                    
        return Open
    
    def __GetShowInViewerFunc(self, filename):
        def OnFeelingViewer(e):
            quotedViewer = "\"" + self.__feelingViewerPath + "\""
            args = ["\"" + self.__feelingViewerPath + "\"", 
                    "\"" + filename + "\""]
            os.spawnv(os.P_DETACH, self.__feelingViewerPath, args)
        return OnFeelingViewer
    
    def __GetCompareImageFunc(self, grid, renderedArea, imageData, type):
        def Compare(e):
            dialog = FCompareSetupDialog(grid, type, self.__testProcedure.GetName(), os.path.basename(imageData.GetTest().GetTestDir()), imageData.GetExecutionName())
            if (dialog.ShowModal() == wx.ID_OK):
                if (renderedArea.GetType() == FImageType.IMAGE):
                    filename = os.path.basename(renderedArea.GetFilename())
                else:
                    filename = "Animation"
                
                title1 = [("Test Procedure", self.__testProcedure.GetName()),
                          ("Test", os.path.basename(
                                        imageData.GetTest().GetTestDir())),
                          ("Execution", imageData.GetExecutionName()),
                          ("Test Filename", filename)]
                title2 = [("Test Procedure", dialog.GetTestProcedure()),
                          ("Test", dialog.GetTest()),
                          ("Execution", dialog.GetExecution()),
                          ("Test Filename", dialog.GetStep())]
                if (dialog.GetShowBlessed()):
                    blessed = imageData.GetBlessedFilenames()
                else:
                    blessed = None
                
                if (renderedArea.GetType() == FImageType.IMAGE):
                    filename = [renderedArea.GetFilename(),]
                else:
                    filename = renderedArea.GetFilename()
                
                # If the user didn't select something to compare against, use the blessed images.
                filename2 = dialog.GetPath()
                if (filename2 == None): 
                    filename2 = imageData.GetBlessedFilenames()
                    title2 = [["Default Blessed"], [" "], [" "], [" "]]
                    blessed = None
                    
                dialog = FComparisonDialog(grid, title1, filename, title2, filename2, blessed)
                dialog.ShowModal()
        return Compare
    
    def __GetDefaultBlessImageFunc(self, grid, renderedArea, imageData):
        def Bless(e):
            test = imageData.GetTest()
            grid.PartialRefreshRemove(test, imageData.GetGridId())

            # Set this still image/animation as the default blessed image.
            busyInfo = wx.BusyInfo("Default blessing image. Please wait...")
            if (renderedArea.GetType() == FImageType.IMAGE):
                test.DefaultBless(renderedArea.GetFilename())
            elif (renderedArea.GetType() == FImageType.ANIMATION):
                test.DefaultBlessAnimation(renderedArea.GetFilename())

            # Update the result and refresh the grid row.
            test.UpdateResult(self.__testProcedure, test.GetCurrentExecution())
            grid.PartialRefreshAdd(test, imageData.GetExecution(), imageData.GetGridId())
            grid.PartialRefreshDone()
            
        return Bless
    
    def __GetReplaceDefaultBlessImageFunc(self, grid, renderedArea, imageData):
        def Bless(e):
            test = imageData.GetTest()
            grid.PartialRefreshRemove(test, imageData.GetGridId())

            # Set this still image/animation as the default blessed image.
            busyInfo = wx.BusyInfo("Replacing default blessed image. Please wait...")
            if (renderedArea.GetType() == FImageType.IMAGE):
                test.ReplaceDefaultBless(renderedArea.GetFilename())
            elif (renderedArea.GetType() == FImageType.ANIMATION):
                test.ReplaceDefaultBlessAnimation(renderedArea.GetFilename())

            # Update the result and refresh the grid row.
            test.UpdateResult(self.__testProcedure, test.GetCurrentExecution())
            grid.PartialRefreshAdd(test, imageData.GetExecution(), imageData.GetGridId())
            grid.PartialRefreshDone()
            
        return Bless

    def __GetBlessImageFunc(self, grid, renderedArea, imageData):
        def Bless(e):
            test = imageData.GetTest()
            grid.PartialRefreshRemove(test, imageData.GetGridId())

            # Bless this still image/animation.
            busyInfo = wx.BusyInfo("Blessing Image. Please wait...")
            if (renderedArea.GetType() == FImageType.IMAGE):
                test.Bless(renderedArea.GetFilename())
            elif (renderedArea.GetType() == FImageType.ANIMATION):
                test.BlessAnimation(renderedArea.GetFilename())
                
            # Update the result and refresh the grid row.
            test.UpdateResult(self.__testProcedure, test.GetCurrentExecution())
            grid.PartialRefreshAdd(test, imageData.GetExecution(), imageData.GetGridId())
            grid.PartialRefreshDone()
        return Bless
    
    def __GetCompareLogFunc(self, grid, renderedArea, imageData):
        def Compare(e):
            if (self.__diffCommand == ""):
                FUtils.ShowWarning(grid.GetParent(), 
                                   "No diff program selected")
                return
            
            dialog = FCompareSetupDialog(grid, FCompareSetupDialog.LOG, 
                    self.__testProcedure.GetName(), 
                    os.path.basename(imageData.GetTest().GetTestDir()),
                    imageData.GetExecutionName())
            if (dialog.ShowModal() == wx.ID_OK):
                command = self.__diffCommand.replace("%base", 
                        "\"" + renderedArea.GetFilename() + "\"")
                command = command.replace("%mine", 
                        "\"" + os.path.abspath(dialog.GetPath()) + "\"")
                os.system("\"" + command + "\"")
        return Compare
    
    def AddContext(self, grid, row, col, menu, position):
        imageData = grid.GetCellValue(row, col)
        if (imageData == None): return
        
        menu.AppendSeparator()
        
        renderedArea = self.__GetRenderedArea(grid, row, col, position)
        if (renderedArea != None):
            
            # Compute the typename for this item.
            if (renderedArea.GetType() == FImageType.IMAGE):
                typename = "Image"
            elif (renderedArea.GetType() == FImageType.LOG):
                typename = "Log"
            elif (renderedArea.GetType() == FImageType.ANIMATION):
                typename = "Animation"
            else:
                typename = ""
                print ("<FImageRenderer> Unexpected type: " + str(renderedArea.GetType()))
            
            id = wx.NewId()
            menuItem = wx.MenuItem(menu, id, "View " + typename)                
            filename = renderedArea.GetFilename()
            if ((renderedArea.GetType() == FImageType.IMAGE) and (self.__IsDaeFile(filename))):
                viewerId = wx.NewId()
                viewerMenuItem = wx.MenuItem(menu, viewerId, "View in Feeling Viewer")
                font = menuItem.GetFont()
                font.SetWeight(wx.BOLD)
                viewerMenuItem.SetFont(font)
                menu.AppendItem(viewerMenuItem)
                
                grid.Bind(wx.EVT_MENU, self.__GetShowInViewerFunc(filename), id = viewerId)
            else:
                font = menuItem.GetFont()
                font.SetWeight(wx.BOLD)
                menuItem.SetFont(font)
            
            menu.AppendItem(menuItem)
            grid.Bind(wx.EVT_MENU, self.__GetOpenFunc(filename, renderedArea.GetType(), grid), id = id)
            
            if ((renderedArea.GetType() == FImageType.IMAGE) and (self.__IsDaeFile(filename))):
                id = wx.NewId()
                menu.Append(id, "Show Default Asset Tags")
                
                def OnContext(e):
                    self.__ShowAssetTags(imageData.GetDefaultFilename())
                
                grid.Bind(wx.EVT_MENU, OnContext, id = id)
                    
            if self.__showCounts and typename != "Log":
                # Create the "Blessed.." sub-menu
                id = wx.NewId()
                blessedMenu = wx.Menu()
                menu.AppendMenu(id, "Bless " + typename, blessedMenu)
            
                # Add to the blessed list and set as the default.
                id = wx.NewId()
                if (((renderedArea.GetType() == FImageType.IMAGE) or
                        (renderedArea.GetType() == FImageType.ANIMATION)) and 
                        self.__showCounts):
                    blessedMenu.Append(id, "Add as Default")
                    grid.Bind(wx.EVT_MENU, self.__GetDefaultBlessImageFunc(grid, renderedArea, imageData), id = id)
                
                # Add to alternative blessed list.
                id = wx.NewId()
                if (((renderedArea.GetType() == FImageType.IMAGE) or
                        (renderedArea.GetType() == FImageType.ANIMATION)) 
                        and self.__showCounts):
                    blessedMenu.Append(id, "Add as Alternate")
                    grid.Bind(wx.EVT_MENU, self.__GetBlessImageFunc(grid, renderedArea, imageData), id = id)
                
                # Replace the default blessed.
                if (imageData.GetTest().HasBlessed()):
                    id = wx.NewId()
                    if (((renderedArea.GetType() == FImageType.IMAGE) or
                            (renderedArea.GetType() == FImageType.ANIMATION)) and 
                            self.__showCounts):
                        blessedMenu.Append(id, "Replace Default")
                        grid.Bind(wx.EVT_MENU, self.__GetReplaceDefaultBlessImageFunc(grid, renderedArea, imageData), id = id)

            # Compare images/animations
            id = wx.NewId()
            if (renderedArea.GetType() == FImageType.LOG):
                grid.Bind(wx.EVT_MENU, self.__GetCompareLogFunc(grid, renderedArea, imageData), id = id)
            elif (self.__showCounts) and (renderedArea.GetType() == FImageType.IMAGE or renderedArea.GetType() == FImageType.ANIMATION):
                menu.Append(id, "Compare " + typename)
                grid.Bind(wx.EVT_MENU, self.__GetCompareImageFunc(grid, renderedArea, imageData, renderedArea.GetType()), id = id)
    
    def __ShowAssetTags(self, filename):
        assetFilename = os.path.abspath(
                FUtils.GetAvailableFilename(ASSET_FILENAME))
        f = open(assetFilename, "w")
        xml.sax.parse(filename, FAssetHandler(f))
        f.close()
        os.system("\"" + assetFilename + "\"")
        os.remove(assetFilename)
    
    def __IsDaeFile(self, filename):
        basename = os.path.basename(filename)
        nameList = basename.rsplit(".", 1)
        
        if (len(nameList) < 2): return False
        
        return (nameList[1].lower() == "dae")
    
    def __GetRenderedArea(self, grid, row, col, position):
        position = grid.CalcUnscrolledPosition(position)
        for renderedArea in self.__renderedAreas[(row, col)]:
            rect = renderedArea.GetRect()
            if (rect.Inside(position)):
                return renderedArea
    
    def Clicked(self, grid, row, col, position):
        if (not self.__renderedAreas.has_key((row, col))): return
        
        renderedArea = self.__GetRenderedArea(grid, row, col, position)
        if (renderedArea != None):
            filename = renderedArea.GetFilename()
            if ((renderedArea.GetType() == FImageType.IMAGE) and 
                    (self.__IsDaeFile(filename))):
                (self.__GetShowInViewerFunc(filename))(None)
            else:
                (self.__GetOpenFunc(filename, renderedArea.GetType(), 
                                    grid))(None)
    
