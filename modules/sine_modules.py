import pandas as pd
import numpy as np
import numpy, scipy.optimize
import pylab as plt

def load_set(stock, data_dir, tail):
    df = pd.read_pickle('{}{}{}'.format(data_dir, stock, tail))
    return df

def fit_sin(tt, yy):
    '''Fit sin to the input time sequence, 
    and return fitting parameters "amp", "omega", "phase", "offset", "freq", "period" and "fitfunc"'''
    tt = numpy.array(tt)
    yy = numpy.array(yy)
    ff = numpy.fft.fftfreq(len(tt), (tt[1]-tt[0]))   # assume uniform spacing
    Fyy = abs(numpy.fft.fft(yy))
    guess_freq = abs(ff[numpy.argmax(Fyy[1:])+1])   # excluding the zero frequency "peak", which is related to offset
    guess_amp = numpy.std(yy) * 2.**0.5
    guess_offset = numpy.mean(yy)
    guess = numpy.array([guess_amp, 2.*numpy.pi*guess_freq, 0., guess_offset])

    def sinfunc(t, A, w, p, c):  return A *numpy.sin(w*t + p) + c
    
    popt, pcov = scipy.optimize.curve_fit(sinfunc, tt, yy, p0=guess)
    A, w, p, c = popt
    f = w/(2.*numpy.pi)
    fitfunc = lambda t: A * numpy.sin(w*t + p) + c
    
    return {"amp": A, 
            "omega": w, 
            "phase": p, 
            "offset": c, 
            "freq": f, 
            "period": 1./f, 
            "fitfunc": fitfunc, 
            "maxcov": numpy.max(pcov), 
            "rawres": (guess,popt,pcov)}

def plot_sin(x, y, res):
    '''
    Plots the data and the sine wave generated
    '''
    #res = fit_sin(x, y)
    print( "Amplitude=%(amp)s, Angular freq.=%(omega)s, phase=%(phase)s, offset=%(offset)s, Max. Cov.=%(maxcov)s" % res )

    plt.plot(x, y, "-k", label="y", linewidth=2)
    #plt.plot(tt, yynoise, "ok", label="y with noise")
    plt.plot(x, res["fitfunc"](x), "r-", label="y fit curve", linewidth=2)
    plt.legend(loc="best")
    plt.show()
    
    
def mesa_wave(x):
    '''
    c code adaptation here: https://github.com/TulipCharts/tulipindicators/blob/master/indicators/msw.c
    image basis https://rtmath.net/helpFinAnalysis/html/e1749c57-2542-4c8e-821f-b48ed8e0213e.htm
    
    best used with pandas rolling function, ex.:
    
        df['close'].rolling(5).apply(mesa_wave, raw=True)
    '''
    N = len(x)
    j = np.arange(0, N)
    
    real = np.sum(np.cos((360 * j) / N) * x)
    imagin = np.sum(np.sin((360* j) / N) * x)
    
    if abs(real) > 0.001:
        phase = np.arctan(real / imagin) #+ 90
    else:
        if imagin < 0:
            phase = np.pi * - 1.0
        else:
            phase = np.pi * 1.0
    
    if real < 0.0:
        phase += 2* np.pi
    phase += np.pi / 2
    if phase < 0.0:
        phase += 2 * np.pi
    if phase > 2 * np.pi:
        phase -= 2 * np.pi
    
    
    sine = np.sin(phase)
    
    return sine