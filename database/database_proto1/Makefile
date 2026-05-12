CXX = g++
CXXFLAGS = -Wall -std=c++17

BUILDDIR = build
TARGET = $(BUILDDIR)/pf_test1

SRCS = pf_test1.cc pf_manager.cc pf_buffermgr.cc pf_hashtable.cc pf_pagehandle.cc
OBJS = $(SRCS:%.cc=$(BUILDDIR)/%.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

$(BUILDDIR)/%.o: %.cc | $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
