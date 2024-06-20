import numpy as np
import matplotlib.pyplot as plt
import os
import glob


# allow run='latest'

def isiterable(p_object):
    try:
        it = iter(p_object)
    except TypeError:
        return False
    return True


def plot_siglent(folder, run=1, peak_center='span center', window=5,
                 xlim=(None, None), snrlim=(None, None),
                 freqlim=(None, None), reload=False, timeunit='sec', low_freq_ignore=5):
    """
    Parameters
    ----------

    folder : int or string
         The folder where the data is located
    run : int
        the run number to load
    peak_center : float or string
        if a number (float) this is the center of the peak in MHz.
        Can also be 'span center' to go to the center of the span.
        Can also be 'track' to attempt to track the peak.
    window : float
        width of the SNR/peak center integration window in MHz.
    xlim : (float, float)
        limits on the x-axis. for example, (10.2, 25.5)
    snrlin : (float, float)
        ylims for the SNR plot
    freqlim : (float, float)
        ylims for the center frequecy plot
    reload : boolean
        determines if the text files should be reloaded
    timeunit : string
        determins the unit for the x-axis. Options: 'hours', 'minutes','seconds'

    """

    fig, axs = plt.subplots(3, 1, figsize=(7, 9), sharex=True)
    ax0, ax1, ax2 = axs

    fig.subplots_adjust(top=0.97, bottom=0.07, right=0.85, left=0.12, wspace=0.1, hspace=0.1)

    cax = fig.add_axes([0.87, 0.70, 0.02, 0.25])  # left, bot, w, h
    logfilename = folder + '/run %04i' % run + '/LOGFILE.txt'
    ns, times = np.loadtxt(logfilename, unpack=True, skiprows=1, delimiter=',', usecols=[0, 1])

    npz_filename = folder + '/run %04i' % run + '/data.npz'

    if reload is False and os.path.exists(npz_filename):
        data = np.load(npz_filename)
        spectra = data['spectra']
        times = data['times']
        freqs = data['freqs']

    else:
        files = glob.glob(folder + '/run %04i' % run + '/Siglent*')
        nfiles = len(files)

        spectra = []

        for n in range(nfiles):
            f = (folder + '/run %04i' % run + '/Siglent-data_' +
                 folder + '_%04i.txt' % n)
            print(f)
            if os.path.exists(f):
                with open(f, 'r') as file:
                    startline = 0
                    while startline < 100:
                        startline += 1
                        line = file.readline()
                        if 'Frequency' in line:
                            break
                if startline == 1:  # old fil: no header, comma delimiter
                    freqs, dBs = np.loadtxt(f, unpack=True, skiprows=1, delimiter=',')
                else:  # new file. Header and space delimited
                    freqs, dBs = np.loadtxt(f, unpack=True, skiprows=startline)

                spectra.append(dBs)
            else:
                print('could not load')
                spectra.append(spectra[-1]*np.nan)

        times = times[:len(spectra)+1]
        spectra = np.array(spectra)

        np.savez_compressed(npz_filename, spectra=spectra, times=times, freqs=freqs)

    if timeunit == 'minutes':
        times = times/60
    elif timeunit == 'hours':
        times = times/3600
    elif timeunit == 'seconds':
        times = times
    else:
        raise ValueError('Time unit not recognized.')

    flipped = np.rot90(spectra)
    extent = (times.min(), times.max(), freqs.min(), freqs.max())

    im = ax0.imshow(flipped, extent=extent, aspect='auto',
                    cmap='inferno', interpolation='nearest')

    ax0.set_ylabel('Frequency (MHz)')

    SP = 10**(0.1 * flipped)
    T, F = np.meshgrid(times, freqs[::-1])
    SP[F < low_freq_ignore] = 0

    if peak_center == 'track':
        centers = np.sum(F*SP, axis=0)/np.sum(SP, axis=0)
    elif peak_center == 'center span':
        centers = times * 0 + np.mean(freqs)
    else:
        centers = times * 0 + peak_center

    axs[0].plot(times, centers + 0.5*window, color='w', ls='dashed', lw=0.5)
    axs[0].plot(times, centers - 0.5*window, color='w', ls='dashed', lw=0.5)

    ind = ((F > (centers + 0.5 * window)) | (F < (centers - 0.5 * window)))

    dB_mask = np.copy(flipped)
    dB_mask[ind] = np.nan

    SP_mask = np.copy(SP)
    SP_mask[ind] = np.nan

    snrs = np.nanmax(dB_mask, axis=0) - np.nanmin(dB_mask, axis=0)
    mean_freqs = np.nansum(F*SP_mask, axis=0)/np.nansum(SP_mask, axis=0)

    mean_freq = np.mean(mean_freqs)
    std = np.std(mean_freqs)

    ax1.plot(times, snrs, label='CEO signal-to-noise ratio\nmean=%.2f dB, stddev=%.2f dB' % (np.mean(snrs), np.std(snrs)))
    ax2.plot(times, mean_freqs, color='C1', label='CEO frequency\nmean=%.2f MHz, stddev=%.2f MHz' % (mean_freq, std))

    ax2.set_xlabel('Time (%s)' % timeunit)
    ax1.set_ylabel('SNR (dB)')

    ax2.set_ylabel('Center frequency (MHz)')

    for ax in axs:
        ax.set_xlim(xlim)

    for ax in (ax1, ax2):
        ax.grid(alpha=0.2, color='k')
        ax.legend(labelcolor='linecolor')

    ax1.set_ylim(snrlim)
    ax2.set_ylim(freqlim)

    ax0.set_ylim(freqlim)

    ax0.set_title(folder + ' - Run %04i' % run)

    cbar = plt.colorbar(im, cax=cax)
    cbar.ax.set_ylabel('Power (dBm)')
    cbar.ax.tick_params(labelsize=8)

    # Now for the slice plotting!

    fig.savefig(folder + '/' + folder + ' - Run %04i' % run + '.png', dpi=200)


plot_siglent('2022-11-07', 4, peak_center=20, window=12, snrlim=(0, 70), timeunit='seconds',
             reload=False, slice_file='SliceQTC 2022-11-07 - 14h-20m-41s.csv')


plt.show()
