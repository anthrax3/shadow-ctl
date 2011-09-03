import curses, os, time
from multiprocessing import Queue

from core import panel, popupPanel, tools

class ScrollPanel(panel.Panel):
    
    def __init__(self, stdscr, name, top, backlog):
        panel.Panel.__init__(self, stdscr, name, top)
        self.data = []
        self.asyncQ = Queue()
        self.backlog = backlog
        self.scrollTop = 0
        self.scrollBottom = 0
        self.scrollHeight = 0
        self.scrollFollow = True
        
    def add(self, output):
        for line in output.split('\n'): self.data.append(line)
        if self.backlog > 0:
            while len(self.data) > self.backlog: self.data.pop(0)
        if self.scrollFollow:
            self.scrollBottom = len(self.data)
            self.scrollTop = max(0, self.scrollBottom - self.scrollHeight)
            
    def get(self):
        copy = list(self.data)
        return copy
        
    def draw(self, width, height):
        output = []
        for item in self.data: 
            lines = tools.splitStr(item, width-2)
            for line in lines: output.append(line)
        
        self.scrollLines = len(output)
        self.scrollHeight = height-1
        self.scrollBottom = min(self.scrollTop + self.scrollHeight, self.scrollLines)
        
        # if we've navigated away from the bottom of the log, stop following new output
        if self.scrollBottom != self.scrollLines: self.scrollFollow = False
        # start following again if we navigate back to the bottom of the log
        else: self.scrollFollow = True
        
        # dont draw unless we have data
        if self.scrollLines > 0:
            yoffset = 0
            if self.isTitleVisible(): 
                self.addstr(yoffset, 0, self.getName(), curses.A_STANDOUT)
                self.addstr(yoffset, len(self.getName()) + 1, "s: save log", curses.A_NORMAL)
                yoffset += 1
                
            self.addScrollBar(self.scrollTop, self.scrollBottom, self.scrollLines, drawTop = yoffset, drawScrollBox = True)
    
            for i in xrange(self.scrollTop, min(self.scrollBottom, len(output))):
                line = output[i]
                self.addstr(yoffset, 3, tools.padStr(line, width-3))
                yoffset += 1
        
    def handleKey(self, key):
        # we only care if they pushed one of the scroll keys
        if tools.isScrollKey(key):
            newScroll = tools.getScrollPosition(key, self.scrollTop, self.scrollHeight, self.scrollLines)
            if self.scrollTop != newScroll:
                self.scrollTop = newScroll
                self.redraw(True)
            return True
        else: return False
        
    def saveLog(self):
        query = "Please enter the path to save the log file, or press ESC to cancel:"
        default = os.path.abspath(os.getenv("HOME") + "/.shadow/cli-" + str(int(time.time())) + ".log")
        
        # use a popup to ask about the path of the file to save
        p = popupPanel.PopupPanel(self.parent, 2, 2)
        p.setVisible(True)
        p.setQuery(query)
        p.setDefaultResponse(default)
        p.redraw(True)
        path = p.getUserResponse()
        
        if path is not None:
            path = os.path.abspath(path)
            d = os.path.dirname(path)
            if not os.path.exists(d): os.makedirs(d)
            with open(path, 'a') as f:
                for line in self.get(): f.write(line)
                
            self.add("Log saved to " + path)
            
    def flush(self):
        """
        Swap messages that other threads put into the async queue in to the data list
        """
        while not self.asyncQ.empty():
            self.add(self.asyncQ.get(timeout=1))
