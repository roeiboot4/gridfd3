import glob
import os
import re
import shutil
import subprocess as sp
import threading
import time
import typing

import astropy.io.fits as fits
import matplotlib.pyplot as plt
import numpy as np
import scipy.interpolate as spint

import outfile_analyser as oa
# noinspection PyUnresolvedReferences
import plotsetup

# %%
starttime = time.time()


class Fd3gridLine:

    def __init__(self, name, limits, samp):
        self.name = name
        self.used_spectra = list()
        self.limits = limits
        self.base = np.arange(limits[0] - 0.0001, limits[1] + 0.0001, samp)
        self.data = list()
        self.noises = list()
        self.mjds = list()
        self.dof = 0
        for j in range(number_of_files):
            with fits.open(allfiles[j]) as hdul:
                try:
                    spec_hdu = hdul['NORM_SPECTRUM']
                except KeyError:
                    print(allfiles[j], 'has no normalized spectrum, skipping')
                    continue
                loglamb = spec_hdu.data['log_wave']
                # check whether base is completely covered
                if loglamb[0] >= self.base[0] or loglamb[-1] <= self.base[-1]:
                    print(allfiles[j], 'is not fully covered')
                    continue
                # check whether spline is present
                try:
                    hdul['LOG_NORM_SPLINE']
                except KeyError:
                    print(allfiles[j], 'has no log_norm_spline')
                    continue
                # determine indices where the line resides
                start = 0
                startline = 0
                endline = 0
                while loglamb[start] < self.base[0]:
                    start += 1
                    startline += 1
                    endline += 1
                # check if start of noise estimation interval is not zero
                if spec_hdu.data['norm_flux'][start] < 0.01:
                    print(allfiles[j], 'has low start of noise interval in line', self.name)
                    continue
                while loglamb[startline] < limits[0]:
                    startline += 1
                    endline += 1
                # check if end of noise estimation interval is not zero or if no data in the estimation interval
                if spec_hdu.data['norm_flux'][startline] < 0.01 or start == startline:
                    print(allfiles[j], 'has low end of noise interval in line', self.name)
                    continue
                while loglamb[endline] < limits[1]:
                    endline += 1
                # check whether end of line is not in interorder spacing of spectrograph
                if spec_hdu.data['norm_flux'][endline] < 0.01:
                    print(allfiles[j], 'has low end of data interval in line', self.name)
                    continue
                self.used_spectra.append(allfiles[j])
                # append in base evaluated flux values
                evals = spint.splev(self.base, hdul['log_NORM_SPLINE'].data[0])
                self.data.append(evals)
                # determine noise near this line
                self.noises.append(np.std(hdul['NORM_SPECTRUM'].data['norm_flux'][start:startline]))
                # record mjd in separate list
                self.mjds.append(hdul[0].header['MJD-obs'])
        self.data = np.array(self.data)
        self.data.setflags(write=False)  # make sure the original data is immutable!
        print(' this line uses {} spectra'.format(len(self.used_spectra)))

    def run(self, wd, iteration: int = None):
        if not iteration:
            print(' making in file')
        self._make_infile(wd, iteration)
        if not iteration:
            print(' making master file')
        self._make_masterfile(wd, iteration)
        if not iteration:
            print(' running gridfd3')
        self._run_fd3grid(wd)
        if not iteration:
            print(' saving output')
        self._save_output(wd, iteration)

    def perturb_spectra(self):
        newdata = np.copy(self.data)
        n = newdata.shape[1]
        m = newdata.shape[0]
        # perturb data
        pert = np.random.default_rng().normal(loc=0, scale=self.noises, size=(n, m))
        return newdata + pert.T

    @staticmethod
    def perturb_orbit():
        return orbit + np.random.default_rng().normal(0, orbit_err, 4)

    def _make_infile(self, wd, iteration=None):
        with open(wd + '/in{}'.format(self.name), 'w') as infile:
            # write first line
            infile.write(wd + "/master{}.obs ".format(self.name))
            infile.write("{} ".format(self.limits[0]))
            infile.write("{} \n".format(self.limits[1]))
            # write the star switches
            if thirdlight:
                infile.write('1 1 1 \n')
            else:
                infile.write('1 1 0 \n')
            # write observation data
            for j in range(len(self.used_spectra)):
                if thirdlight:
                    infile.write(
                        str(self.mjds[j]) + ' 0 {} {} {} {}\n'.format(self.noises[j], lfs[0], lfs[1], lfs[2]))
                # correction, noise, lfA, lfB, lfC
                else:
                    infile.write(
                        str(self.mjds[j]) + ' 0 {} {} {}\n'.format(self.noises[j], lfs[0], lfs[1]))
                # correction, noise, lfA, lfB
            if iteration and perturb_orbit:
                params = self.perturb_orbit()
            else:
                params = orbit
            infile.write('1 0 0 0 0 0 \n')  # dummy parameters for the wide AB--C orbit
            # write the A-B orbital params
            infile.write('{} {} {} {} 0\n'.format(params[0], params[1], params[2], params[3]))  # 0 is the Deltaomega
            # write rv ranges and step size
            infile.write('{}\n'.format(k1str))
            infile.write('{}\n'.format(k2str))

    def _make_masterfile(self, wd, iteration=None):
        with open(wd + '/master{}.obs'.format(self.name), 'w') as obsfile:
            obsfile.write('# {} X {} \n'.format(len(self.used_spectra) + 1, len(self.base)))
            master = [self.base]
            if iteration and perturb_spectra:
                data = self.perturb_spectra()
            else:
                data = self.data
            for ii in range(len(data)):
                master.append(data[ii])
            towrite = np.array(master).T
            for ii in range(len(towrite)):
                obsfile.write(" ".join([str(num) for num in towrite[ii]]))
                obsfile.write('\n')

    def _run_fd3grid(self, wd):
        with open(wd + '/in{}'.format(self.name)) as inpipe, open(wd + '/out{}'.format(self.name), 'w') as outpipe:
            sp.run(['./fd3grid'], stdin=inpipe, stdout=outpipe)

    def _save_output(self, wd, iteration):
        with open(wd + '/out{}'.format(self.name)) as f:
            llines = f.readlines()
            llines.pop(0)
            kk1s = np.zeros(len(llines))
            kk2s = np.zeros(len(llines))
            cchisq = np.zeros(len(llines))
            for j in range(len(llines)):
                lline = re.split('[ ]|(?![\d.])', llines[j])
                kk1s[j] = np.float64(lline[0])
                kk2s[j] = np.float64(lline[1])
                cchisq[j] = np.float64(lline[2])
        chisqdir = wd + '/chisqs'
        if not os.path.isdir(chisqdir):
            os.mkdir(chisqdir)
        np.savez(chisqdir + '/chisq{}{}'.format(self.name, iteration if iteration is not None else ''), k1s=kk1s,
                 k2s=kk2s, chisq=cchisq)
        self.dof = len(self.used_spectra) * len(self.base)


class Fd3gridThread(threading.Thread):

    def __init__(self, threadno, iterations, fd2gridlines: typing.List[Fd3gridLine]):
        super().__init__()
        self.threadno = threadno
        self.wd = obj + "/thread" + str(threadno)
        self.fd2gridlines = fd2gridlines
        self.iterations = iterations
        self.threadtime = time.time()
        self.chisqs = list()
        print('Thread {} will execute {} iterations.'.format(self.threadno, self.iterations))
        # create directory for this thread
        try:
            shutil.rmtree(self.wd)
        except OSError:
            pass
        try:
            os.mkdir(self.wd)
        except FileExistsError:
            pass
        # create k1file, k2flie to put them empty if they existed
        with open(self.wd + '/k1file', 'w'), open(self.wd + '/k2file', 'w'):
            pass

    def run(self) -> None:
        try:
            for ii in range(self.iterations):
                # execute fd3gridline runs
                print('Thread {} running gridfd3 iteration {}...'.format(self.threadno, ii + 1))
                for ffd2line in self.fd2gridlines:
                    ffd2line.run(self.wd, ii + 1)
                print('estimated time to completion of thread {}: {}h'.format(self.threadno,
                                                                              (time.time() - self.threadtime) * (
                                                                                      self.iterations - ii - 1) / 3600))
                self.threadtime = time.time()
        except Exception as e:
            print('Exception occured when running gridfd3:', e)


#######
# input
obj = 'LB-1/HERMES'
monte_carlo = False
N = 3000
dim = 1
k1str = '52.94 52.94 0.01'
k2str = '0.5 25 0.5'
orbit = (78.7999, 2458845.5394 - 2400000.5, 0, 270)  # p, t0, e, omega(A)
orbit_err = (0.0097, 0, 0, 0)
perturb_orbit = True
perturb_spectra = True
thirdlight = False
lfs = [0.6, 0.4]

# enter ln(lambda/A) range and name of line
lines = dict()
# lines['Hzeta'] = (8.2630, 8.2685)
# lines['Hepsilon'] = (8.2845, 8.2888)
lines['HeI+II4026'] = (8.2990, 8.302, 2e-5)
lines['Hdelta'] = (8.3170, 8.3215, 2e-5)
# lines['SiIV4116'] = (8.3215, 8.3238)
# lines['HeII4200'] = (8.3412, 8.3444)
lines['Hgamma'] = (8.3730, 8.3785, 2e-5)
lines['HeI4471'] = (8.4047, 8.4064, 2e-5)
# lines['HeII4541'] = (8.4195, 8.4226)
# lines['NV4604+4620'] = (8.4338, 8.4390)
# lines['HeII4686'] = (8.4510, 8.4534)
lines['Hbeta'] = (8.4860, 8.4920, 2e-5)
# lines['HeII5411'] = (8.5940, 8.5986)
# lines['OIII5592'] = (8.6281, 8.6300)
# lines['CIII5696'] = (8.6466, 8.6482)
# lines['FeII5780'] = (8.6617, 8.6627)
# lines['CIV5801'] = (8.6652, 8.6667)
# lines['CIV5812'] = (8.6668, 8.6685)
lines['HeI5875'] = (8.6777, 8.6794, 2e-5)
lines['Halpha'] = (8.7865, 8.7920, 2e-5)
lines['HeI6678'] = (8.805, 8.8095, 2e-5)
######

print('starting setup...')
if not os.path.isdir(obj):
    os.mkdir(obj)
spec_folder = None
try:
    spec_folder = glob.glob('/Users/matthiasf/Data/Spectra/' + obj)[0]
except IndexError:
    print('no spectra folder of object found')
    exit()

print('spectroscopy folder is {}\n'.format(spec_folder))

# all fits files in this directory
allfiles = glob.glob(spec_folder + '/**/*.fits', recursive=True)
number_of_files = len(allfiles)

if number_of_files == 0:
    print('no spectra found')
    exit()

K = len(lines)
fd2lines = list()
print('building fd2gridline object for:')
for line in lines.keys():
    print(' {}'.format(line))
    fd2lines.append(Fd3gridLine(line, lines[line][0:2], lines[line][2]))

if monte_carlo:
    # create threads
    cpus = os.cpu_count()
    print('number of threads will be {}'.format(cpus))
    print('each thread will have {} iterations to complete'.format(N / cpus))
    atleast = int(N / cpus)
    remainder = int(N % cpus)
    threads = list()
    for i in range(remainder):
        threads.append(Fd3gridThread(i + 1, atleast + 1, fd2lines))
    for i in range(remainder, cpus):
        threads.append(Fd3gridThread(i + 1, atleast, fd2lines))

    setuptime = time.time()
    print('setup took {}s\n'.format(setuptime - starttime))

    for thread in threads:
        print('starting thread')
        thread.start()

    for thread in threads:
        thread.join()

    print('All runs done in {}h, see you later!'.format((time.time() - starttime) / 3600))
else:
    setuptime = time.time()
    print('setup took {}s\n'.format(setuptime - starttime))
    for fd2line in fd2lines:
        print('handling {} line'.format(fd2line.name))
        fd2line.run(obj)
# %%
files = list()
dof = sum(fd2line.dof for fd2line in fd2lines)
for key in lines.keys():
    files.append(glob.glob(obj + '/chisqs/chisq{}.npz'.format(key))[0])
k1s, k2s, chisq = oa.file_analyser(files[0])
for i in range(1, len(files)):
    k1shere, k2shere, chisqhere = oa.file_analyser(files[i])
    chisq += chisqhere
fig = plt.figure()
if dim == 2:
    ax = oa.plot_contours(fig, k1s, k2s, chisq / dof)
    ax.set_title(r"$\chi^2_{\textrm{red}}$")
    ax.set_xlabel(r'$K_1(\si{\km\per\second})$')
    ax.set_ylabel(r'$K_2(\si{\km\per\second})$')
    oa.mark_minimum(ax, k1s, k2s, chisq, r'$\chi^2_\textrm{red,min}$')
    ax.legend(loc=2)
    plt.tight_layout()
    fig.savefig('chisq.png', dpi=200)
    print(np.argmin(chisq))
else:
    ax = oa.plot_oneDee(fig, k2s, chisq / dof)
    ax.set_title(r"$\chi^2_{\textrm{red}}, K_1 = $" + " " + str(min(k1s)) + " " + r'$\si{\km\per\second}$')
    ax.set_xlabel(r'$K_2(\si{\km\per\second})$')
    plt.grid()
    plt.tight_layout()
    fig.savefig('chisq.png', dpi=200)
