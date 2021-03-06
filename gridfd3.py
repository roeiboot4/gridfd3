"""
User script showing the typical use case for gridfd3.
First a list of files containing the relevant spectra is globbed.
Next, we specify the orbital parameters and the RV semi-amplitude ranges that need to be explored, and various other
parameters such as the sampling rate and light factors
"""

import glob
import os
import pathlib
import time

import modules.gridfd3classes as fd3classes


# input
# define working directories
obj = '9_Sgr/testgamma'
# gridfd3folder = obj + '/' + str(datetime.today().strftime('%y%m%dT%H%M%S'))
gridfd3folder = obj
fd3folder = gridfd3folder + '/fd3'

# find locations of your spectra
spectra_set = ['9_Sgr']  # allows for subsetting spectra
try:
    spec_folder = list()
    for folder in spectra_set:
        spec_folder.append(
            glob.glob('/Users/matthiasf/data/spectra/' + folder)[0])  # actual path to your folder containing spectra
except IndexError:
    spec_folder = None
    print('no spectra folder of object found')
    exit()

# geometrical orbit elements and its error. error is ignored if not monte_carlo
orbit = (3261, 56547, 0.648, 30.8, -5)  # p, t0, e, omega(A), Delta\gamma

# K1 and K2 ranges to be explored, in string form: 'left right step', all in km/s
k1str = '15 45 1'
k2str = '40 65 1'

# light factors of your components (if thirdlight, give three)
lfs = [0.57, 0.43]

# Indicate if you want the model spectra to be computed
back = False


# these are the full reported MCMC errors
# orbit_err = np.array([[68, 12, 0.009, 2.3]])  # make this 2D so we can transpose if needed

# optional: correlation matrix
# these are the single minimization errors that provided the correlation matrix
# orbit_err_unscale = np.array([[14.2, 2.396, 0.002, 0.452]])
# the correlation matrix
# orbit_covar_unscale = np.array(
#     [[2.016706010889813285e+02, 2.650853464144408811e+00, 1.653940436054600338e-02, 1.510087481644369234e+00],
#      [2.650853464144408811e+00, 5.739323098131123402e+00, 3.250949346561587527e-03, 1.040789875201268533e+00],
#      [1.653940436054600338e-02, 3.250949346561587527e-03, 3.299601439411175585e-06, 6.442714780292257666e-04],
#      [1.510087481644369234e+00, 1.040789875201268533e+00, 6.442714780292257666e-04, 2.043357582025700225e-01]])
# # now we scale the correlation matrix to the full error
# scale = np.matmul((orbit_err / orbit_err_unscale).T, orbit_err / orbit_err_unscale)
# orbit_covar_scale = scale * orbit_covar_unscale

# do you want a (static) third component to be found?
thirdlight = False

# sampling of your spectra in angstrom
sampling = 0.03

# enter wavelength range(s) in natural log of wavelength and give name of line. Must be a dict.
lines = dict()
# lines['HeI4009'] = (4002, 4016)
# lines['HeI+II4026'] = (4016, 4035)
# lines['NIV4058'] = (4050, 4065)
# lines['SiIV4089'] = (4086, 4092)
lines['Hdelta'] = (4085, 4120)
# lines['SiIV4116'] = (4113, 4118)
# lines['HeI4121'] = (4114, 4127)
# lines['HeI4143'] = (4135, 4152)
lines['HeII4200'] = (4188, 4212)
lines['Hgamma'] = (4320, 4355)
# lines['NIII4379'] = (4370, 4384)
# lines['HeI4387'] = (4380, 4395)
# lines['HeI4471'] = (4465, 4478)
lines['HeII4541'] = (4530, 4553)
# lines['FeII4584'] = (4578, 4589)
# lines['CIII4650'] = (4625, 4660)
lines['HeII4686'] = (4676, 4694)
# lines['HeI4713'] = (4704, 4720)
lines['Hbeta'] = (4843, 4877)
# lines['HeI4922'] = (4913, 4930)
# lines['HeI5016'] = (5001, 5025)
# lines['FeII5167'] = (5162, 5175)
# lines['FeII5198'] = (5190, 5205)
# lines['FeII5233'] = (5225, 5238)
# lines['FeII5276'] = (5270, 5282)
# lines['FeII5316+SII5320'] = (5310, 5325)
# lines['FeII5362'] = (5356, 5368)
lines['HeII5411'] = (5397, 5425)
# lines['OIII5592'] = (5583, 5600)
# lines['CIII5696'] = (5680, 5712)
# lines['FeII5780'] = (5774, 5787)
# lines['CIV5801+12'] = (5798, 5817)
lines['HeI5875'] = (5864, 5884)
# lines['Halpha'] = (6550, 6578)
# lines['HeI6678'] = (6667, 6700)
# lines['OI8446'] = (8437, 8455)
# lines['range'] = (4010, 5885)


############################################################
# Here we start our actual runs


def run_join_threads(threads):
    """
    runs and joins the threads passed in the list 'threads'. Also catches any exceptions thrown in the threads
    :param threads: list of threads to be run and joined
    """
    for thread in threads:
        try:
            thread.start()
        except Exception as e:
            print(repr(thread), e)

    for thread in threads:
        thread.join()


starttime = time.time()
print('starting setup...')
print('orbit is:', orbit)
print('lightfactors are:', lfs)
print('spectroscopy folder is {}\n'.format(spec_folder))

# all fits files in this directory
allfiles = list()
for folder in spec_folder:
    allfiles.extend(glob.glob(folder + '/**/*.fits', recursive=True))

if len(allfiles) == 0:
    print('no spectra found')
    exit()
K = len(lines)
if K == 0:
    print('no lines selected')
    exit()

# make working directories
try:
    pathlib.Path(gridfd3folder).mkdir(parents=True)
except FileExistsError:
    print('folder already exists, I will overwrite in this directory! Do you want to continue? [y]/n')
    ans = input()
    while True:
        if ans == 'n':
            print('exiting...')
            exit()
        elif ans == '' or ans == 'y':
            break
        else:
            print('answer \'\' or y or n')
            ans = input()

if pathlib.Path(gridfd3folder + '/chisqs').exists():
    for file in glob.glob(gridfd3folder + '/chisqs/**'):
        os.remove(file)

pathlib.Path(fd3folder).mkdir(parents=True, exist_ok=True)
# save the run_fd3 parameters for later reference
with open(gridfd3folder + "/params.txt", 'w') as paramfile:
    paramfile.write('orbit\t' + str(orbit) + '\n')
    # paramfile.write('orbit_err\t' + str(orbit_err) + '\n')
    paramfile.write('lightfactors\t' + str(lfs) + '\n')
    paramfile.write('sampling\t' + str(sampling) + '\n')
    paramfile.write('k1s\t' + k1str + '\n')
    paramfile.write('k2s\t' + k2str + '\n')
    paramfile.write('spectra\t' + str(spectra_set) + '\n')
    paramfile.write('lines used:\n')
    for line, bounds in lines.items():
        paramfile.write(str(line) + ' ' + str(bounds) + '\n')

# build the line objects
fd3lineobjects = list()
print('building fd3gridline object for:')
for line in lines.keys():
    print(' {}'.format(line))
    fd3lineobjects.append(
        fd3classes.Fd3class(line, lines[line], sampling, allfiles, thirdlight, orbit, lfs=lfs, k1s=k1str, k2s=k2str))

# build the threads
print('building threads')
cpus = os.cpu_count()
gridthreads = list()
d3threads = list()


# method for clearing the list of threads and populating them with fresh ones to be run anew
def new_threads():
    d3threads.clear()
    gridthreads.clear()
    for ffd3line in fd3lineobjects:
        gridthreads.append(fd3classes.GridFd3Thread(gridfd3folder, ffd3line))
        d3threads.append(fd3classes.Fd3Thread(fd3folder, ffd3line))


# actually make new threads
new_threads()
setuptime = time.time()
print('setup took {}s\n'.format(setuptime - starttime))
# start the gridfd3 runs, do i iterations of grid disentangling, normal fd3 separation and normalization of the
# separated lines
print('starting runs!')
i = 0
now = time.time()
# run gridfd3
run_join_threads(gridthreads)
print('run {} done in {}h'.format(i + 1, (time.time() - now) / 3600))
# mink1, mink2 = oa.get_min_of_run(gridfd3folder)
# print('minimum of the last run_fd3 is', mink1, mink2)
#
# for fd3line in fd3lineobjects:
#     fd3line.set_k1(mink1)
#     fd3line.set_k2(mink2)
# # run standard fd3
# run_join_threads(d3threads)
# # recombine_and_renorm
# print('renormalizing')
# for fd3line in fd3lineobjects:
#     fd3line.recombine_and_renorm()
# i += 1
# # reset thread lists with fresh threads
# new_threads()
print('Thanks for your patience! You waited a whopping {} hours!'.format((time.time() - starttime) / 3600))
