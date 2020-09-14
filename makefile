
all : clean gridfd3 fd3

clean :
	rm -f ./bin/* ./src/**/*.o

gridfd3 : src/gridfd3/fd3grid.o src/gridfd3/fd3sep.o src/gridfd3/triorb.o src/kepler.o src/mxfuns.o
	${CC} -Wall src/gridfd3/fd3grid.o src/gridfd3/fd3sep.o src/gridfd3/triorb.o src/kepler.o src/mxfuns.o \
	-lgsl -lgslcblas -lm -o bin/$@

fd3 : src/fd3/fd3.o src/fd3/fd3sep.o src/fd3/triorb.o src/kepler.o src/mxfuns.o
	${CC} -Wall src/fd3/fd3.o src/fd3/fd3sep.o src/fd3/triorb.o src/kepler.o src/mxfuns.o \
	-lgsl -lgslcblas -lm -o bin/$@