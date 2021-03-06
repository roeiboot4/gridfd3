import glob

import numpy as np
import scipy.optimize as spopt
import scipy.special as sps


def file_parser(ffile):
    """
    parses a gridfd3 output file
    :param ffile: file to parse
    :return: the unique k1s, k2s and a chisq matrix corresponding to those k1, k2s.
    """
    ffile = np.load(ffile)
    kk1s = ffile['k1s']
    kk1s = np.unique(kk1s)
    kk2s = ffile['k2s']
    kk2s = np.unique(kk2s)
    cchisqhere = ffile['chisq']
    cchisqhere = cchisqhere.reshape((len(kk1s), len(kk2s)))
    return kk1s, kk2s, cchisqhere


def plot_contours(ffig, kk1s, kk2s, cchisq, ddof, error=False):
    """
    plots the reduced chisq contours on a figure
    :param ffig: figure to plot on
    :param kk1s: k1 axis
    :param kk2s: k2 axis
    :param cchisq: chisquares
    :param ddof: degrees of freedom
    :return: plt axis object which is plotted
    """
    aax = ffig.add_subplot(111)
    k2grid, k1grid = np.meshgrid(kk2s, kk1s)
    cont = aax.contourf(k1grid, k2grid, cchisq / ddof, levels=10, cmap='inferno')
    if error:
        factor = np.min(cchisq) / ddof
        p = 1 - sps.gammainc(ddof / 2, (cchisq / factor) / 2)

        def onesigma(ccchisq):
            """
            defines the one sigma level
            :param ccchisq: chisqs
            :return: 1sig level chisq
            """
            return 0.683 - sps.gammainc(ddof / 2, (ccchisq / factor) / 2)
        print(rt := spopt.root_scalar(onesigma, x0=np.min(cchisq), bracket=[np.min(cchisq), np.max(cchisq)]).root / ddof)
        aax.contour(k1grid, k2grid, p, levels=[rt], colors='red')
        ffig.colorbar(cont, ax=aax)
    return aax


def plot_uncertainty(ffig, kk1s, kk2s, cchisq, ddof):
    """
    plot the 2D uncertainty contour
    :param ffig: figure to plot on
    :param kk1s: k1 axis
    :param kk2s: k2 axis
    :param cchisq: chisq grid
    :param ddof: degrees of freedom
    :return: plt axis object which is plotted
    """
    aax = ffig.add_subplot(111)
    factor = np.min(cchisq) / ddof
    p = 1 - sps.gammainc(ddof / 2, (cchisq / factor) / 2)
    k2grid, k1grid = np.meshgrid(kk2s, kk1s)
    contour = aax.contourf(k1grid, k2grid, p, cmap='inferno')
    ffig.colorbar(contour, ax=aax)
    return aax


def plot_oneDee(ffig, ks, cchisq, ddof, num):
    """
    plots a 1D slice of the chisq grid
    :param ffig: figure to plot on
    :param ks: k axis
    :param cchisq: chisq values corresponding to the ks provided
    :param ddof: degrees of freedom
    :param num: give 1 or 2: is this K1 or 2?
    :return: plt axis object which is plotted
    """
    axx = ffig.add_subplot(111)
    axx.plot(ks, cchisq / ddof)
    minimum = ks[np.argmin(cchisq)]
    onesigma, plus, mins = oneDee_sigma(ks, cchisq, ddof)
    try:
        axx.hlines(onesigma / ddof, ks[0], ks[-1], colors='r')
        axx.text(np.min(ks), (np.max(cchisq) + np.min(cchisq)) / ddof / 2,
                 r'$K_{} = {}^{{+ {}}}_{{- {}}}$'.format(num, minimum, np.round(plus - minimum, 2), np.round(minimum - mins, 2)))
    except TypeError as ee:
        print(ee, 'cannot plot errors if they dont exist')
        axx.text(np.min(ks), (np.max(chisq) + np.min(chisq)) / ddof / 2, 'error outside grid')
    return axx


def oneDee_sigma(ks, cchisq, ddof):
    """
    finds the minimum of a chisq slice and the 1 sigma errors
    :param ks: k axis
    :param cchisq: corresponding chisq values
    :param ddof: degrees of freedom
    :return: minimal chisq, 1sigma chisq value, upper error, lower error
    """
    minn = np.min(cchisq)
    factor = minn / ddof

    def onesigma(ccchisq):
        """
        defines the one sigma level
        :param ccchisq: chisqs
        :return: 1sig level chisq
        """
        return 0.68 - sps.gammainc(ddof / 2, (ccchisq / factor) / 2)

    try:
        ones = spopt.root_scalar(onesigma, x0=np.min(cchisq), bracket=[np.min(cchisq), np.max(cchisq)]).root
        ii = len(ks) - 1
        while cchisq[ii] > ones:
            ii -= 1
        plus = ks[ii + 1] if ii != len(ks) - 1 else ks[-1]
        ii = 0
        while cchisq[ii] > ones:
            ii += 1
        mins = ks[ii - 1] if ii != 0 else ks[0]
    except ValueError as ee:
        print(ee, 'no root found in root_scalar')
        ones, plus, mins = None, None, None
    return ones, plus, mins


def get_minimum(kk1s, kk2s, cchisq):
    """
    finds the minimal k1 and k2 of this chisq grid
    :param kk1s: k1 axis
    :param kk2s: k2 axis
    :param cchisq: chisq gr  id
    :return: k1, k2 for which chisq is minimal
    """
    iidx = list(np.unravel_index(np.argmin(cchisq), cchisq.shape))
    mink1 = kk1s[iidx[0]]
    mink2 = kk2s[iidx[1]]
    return mink1, mink2


def get_min_idx(cchisq):
    """
    finds the indices of the minimal chisq value
    :param cchisq: chisq grid
    :return: array of indices
    """
    return np.unravel_index(np.argmin(cchisq), cchisq.shape)


def mark_minimum(aax, kk1s, kk2s, cchisq, label):
    """
    marks the minimum chisq value on this axis
    :param aax: axis object to plot on
    :param kk1s: k1 axis
    :param kk2s: k2 axis
    :param cchisq: chisq grid
    :param label: a label to add to the legend
    """
    mink1, mink2 = get_minimum(kk1s, kk2s, cchisq)
    aax.plot([mink1], [mink2], 'ro', ms=5, label=label)


def get_min_and_plot(kk1s, kk2s, cchisq, ddof, name):
    """
    convenience method to find the minimum chisq and immediately plot it on a figure
    :param kk1s: k1 axis
    :param kk2s: k2 axis
    :param cchisq: chisq grid
    :param ddof: degrees of freedom
    :param name: name of the savefile
    """
    minima = get_minimum(kk1s, kk2s, cchisq)
    idx = get_min_idx(cchisq)
    print(name, minima, cchisq[idx] / ddof)

    if len(np.unique(kk1s)) > 1:
        ddof -= 2
        fig = plt.figure()
        ax = plot_contours(fig, kk1s, kk2s, cchisq, ddof)
        mark_minimum(ax, kk1s, kk2s, cchisq, r"$\chi^2_{\textrm{red,min}}" + " = {}, {}$".format(minima[0], minima[1]))
        ax.legend(loc=2)
        ax.set_title(r"$\chi^2_{\textrm{red}}$ " + name)
        ax.set_xlabel(r'$K_1(\si{\km\per\second})$')
        ax.set_ylabel(r'$K_2(\si{\km\per\second})$')
        plt.grid()
        plt.tight_layout()
        fig.savefig(folder + '/chisq{}.png'.format(name), dpi=200)
        plt.close(fig)

        fig = plt.figure()
        ax = plot_uncertainty(fig, kk1s, kk2s, cchisq, ddof)
        ax.set_title(r'$1-P(\nu/2, \chi^2/2)$ ' + name)
        ax.set_xlabel(r'$K_1(\si{\km\per\second})$')
        ax.set_ylabel(r'$K_2(\si{\km\per\second})$')
        plt.tight_layout()
        fig.savefig(folder + '/error{}.png'.format(name), dpi=200)
        plt.close(fig)

        fig = plt.figure(figsize=(4, 6))
        ax = plot_oneDee(fig, kk1s, cchisq[:, idx[1]], ddof, 1)
        ax.set_title(r"$\chi^2_{\textrm{red}}$ " + name)
        ax.set_xlabel(r'$K_1(\si{\km\per\second})$')
        ax.set_ylabel(r'$\chi_{\textrm{red}}^2$')
        # plt.grid()
        # plt.tight_layout()
        fig.savefig(folder + '/chisqmargk2{}.png'.format(name))
        plt.close(fig)

        fig = plt.figure(figsize=(4, 6))
        ax = plot_oneDee(fig, kk2s, cchisq[idx[0], :], ddof, 2)
        ax.set_title(r"$\chi^2_{\textrm{red}}$ " + name)
        ax.set_xlabel(r'$K_2(\si{\km\per\second})$')
        ax.set_ylabel(r'$\chi_{\textrm{red}}^2$')
        # plt.grid()
        # plt.tight_layout()
        fig.savefig(folder + '/chisqmargk1{}.png'.format(name), dpi=200)
        plt.close(fig)
    else:
        ddof -= 1
        fig = plt.figure(figsize=(4, 6))
        ax = plot_oneDee(fig, kk2s, cchisq[idx[0], :], ddof, 2)
        ax.set_title(r"$\chi^2_{\textrm{red}}$ " + name)
        ax.set_xlabel(r'$K_2(\si{\km\per\second})$')
        ax.set_ylabel(r'$\chi_{\textrm{red}}^2$')
        # plt.grid()
        # plt.tight_layout()
        fig.savefig(folder + '/chisqmargk1{}.png'.format(name), dpi=200)
        plt.close(fig)


def get_min_of_run(wd):
    files = glob.glob(wd + '/chisqs/*')
    # parse first file
    kk1s, kk2s, cchisq = file_parser(files[0])
    # add up chisq
    for ii in range(1, len(files)):
        _, _, cchisqhere = file_parser(files[ii])
        cchisq += cchisqhere
    # print its minimum
    return get_minimum(kk1s, kk2s, cchisq)


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import plotsetup  # noqa
    import sys

    folder = sys.argv[1]
    lines = glob.glob(folder + '/chisqs/chisq*')
    for i in range(len(lines)):
        lines[i] = lines[i].rsplit('.', maxsplit=1)[0].rsplit('chisq', maxsplit=1)[-1]
    totdof = 0
    totchisq = 0
    for line in lines:
        chisqfiles = list()
        infiles = list()
        # find all files present
        print('finding', line, '...')
        try:
            chisqfiles.append(glob.glob(folder + '/chisqs/chisq{}.npz'.format(line))[0])
        except IndexError as e:
            print(e, 'cannot find {}'.format(line))
            continue
        infiles.append(glob.glob(folder + '/in{}'.format(line))[0])
        # of those present, add dof
        if len(infiles) == 0:
            continue
        dof = 0
        for file in infiles:
            with open(file) as f:
                dofhere = int(f.readlines()[-1])
                dof += dofhere
                totdof += dofhere
        # parse first file
        k1s, k2s, chisq = file_parser(chisqfiles[0])
        totchisq += chisq
        # add up chisq
        for i in range(1, len(chisqfiles)):
            _, _, chisqhere = file_parser(chisqfiles[i])
            chisq += chisqhere
        # print its minimum
        get_min_and_plot(k1s, k2s, chisq, dof, line)
    # get the aggregate chisq plot
    get_min_and_plot(k1s, k2s, totchisq, totdof, 'all')
