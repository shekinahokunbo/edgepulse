CXX=clang++
CXXFLAGS=-O3 -std=c++17 -fPIC

UNAME_S := $(shell uname -s)

all: libpredictor

ifeq ($(UNAME_S),Darwin)
libpredictor: libpredictor.dylib
libpredictor.dylib: cpp/predictor.cpp cpp/predictor.h
	$(CXX) $(CXXFLAGS) -dynamiclib -o $@ cpp/predictor.cpp
else
libpredictor: libpredictor.so
libpredictor.so: cpp/predictor.cpp cpp/predictor.h
	$(CXX) $(CXXFLAGS) -shared -o $@ cpp/predictor.cpp
endif

clean:
	rm -f libpredictor.so libpredictor.dylib
