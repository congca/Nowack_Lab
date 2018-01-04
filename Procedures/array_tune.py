"""
# Limit the number of attempts @ each tuning step
# Figure out when resets are required
# Record traces when tuning is done
Add offset to lock point  (not just the mean)
"""
from matplotlib import pyplot as plt
import numpy as np
from ..Utilities.save import Measurement
from ..Procedures.daqspectrum import SQUIDSpectrum
from ..Procedures.mutual_inductance import MutualInductance2

class ArrayTune(Measurement):
    instrument_list = ["daq", "squidarray", "preamp"]
    _daq_inputs = ["saa", "test"]
    _daq_outputs = ["test"]

    def __init__(self,
                 instruments,
                 squid_bias,
                 squid_tol = 100e-3,
                 aflux_tol = 10e-3,
                 sflux_offset = 0.0,
                 aflux_offset = 0.0):
        """Given a lock SAA, tune the input SQUID and lock it.
        Args:
        instruments (dict): Dictionary of instruments
        squid_bias (float): Bias point for SQUID lock
        squid_tol (float): Allowed DC offset for the locked SQUID
        offset (float): Tune the lockpoint up/down on the SQUID characaristic.
        """
        super(ArrayTune, self).__init__(instruments=instruments)
        self.instruments = instruments
        self.squid_bias = squid_bias
        self.conversion = 10 # Conversion between mod current and voltage
        self.squid_tol = squid_tol
        self.aflux_tol = aflux_tol
        self.sflux_offset = sflux_offset
        self.aflux_offset = aflux_offset

    def acquire(self):
        """Ramp the modulation coil current and monitor the SAA response."""
        # Send TTL pulse on "test"
        data = {"test": 2*np.ones(2000)}
        # Record test
        ret = self.daq.send_receive(data, chan_in = ["saa", "test"],
                                    sample_rate=100000)
        # Zero the DAQ output
        self.daq.outputs["test"].V = 0
        return ret['t'], ret["test"], ret["saa"], 

    def tune_squid_setup(self):
        """Configure SAA for SQUID tuning."""
        self.squidarray.lock("Array")
        self.squidarray.S_flux_lim = 150
        self.squidarray.S_flux = 0
        self.squidarray.testInput = "S_flux"
        self.squidarray.testSignal = "On"
        self.squidarray.S_bias = self.squid_bias
        self.squidarray.sensitivity = "High"
        self.squidarray.reset()

    def tune_squid(self, attempts=5):
        """Tune the SQUID and adjust the DC SAA flux."""
        self.tune_squid_setup()
        self.char = self.acquire()
        error = np.mean(self.char[-1]) - self.aflux_offset
        if np.abs(error) < self.aflux_tol:
            return self.lock_squid()
        elif attempts == 0:
            print("could not tune array flux.")
            return False
        else:
            self.adjust("A_flux", error)
            return self.tune_squid(attempts = attempts-1)

    def lock_squid(self, attempts=5):
        """Lock the SQUID and adjust the DC SQUID flux."""
        self.squidarray.lock("Squid")
        self.squidarray.testSignal = "Off"
        self.squidarray.reset()
        ret = self.daq.monitor(["saa"], 0.01, sample_rate = 100000)
        error = np.mean(ret["saa"]) - self.sflux_offset
        print(error)
        if np.abs(error) < self.squid_tol:
            print("locked with {} attempts".format(5-attempts))
            return True
        elif attempts == 0:
            print("could not tune SQUID flux.")
            return False
        else:
            self.adjust("S_flux", error)
            return self.lock_squid(attempts - 1)

    def adjust(self, attr, error):
        """Adjust DC flux to center the trace @ 0 V."""
        value = getattr(self.squidarray, attr)
        if value + error * self.conversion < 0:
            # Force a jump by resetting
            setattr(self.squidarray, attr, value + 50)
        elif value + error * self.conversion > 150:
            setattr(self.squidarray, attr, 0)
        else:
            # Directly correct the offset
            setattr(self.squidarray, attr, value + self.conversion * error)
        self.squidarray.reset()

    def plot(self):
        fig, ax = plt.subplots(1,3,figsize=(12,4))
        # Plot the charactaristic
        ax[0].plot(self.char[1], self.char[2])
        ax[0].set_xlabel("Test Signal (V)")
        ax[0].set_ylabel("SAA Signal (V)", size="medium")

        # Plot the spectrum
        ax[2].loglog(self.spectrum.f,
                     self.spectrum.psdAve * self.spectrum.conversion)
        ax[2].set_xlabel("Frequency (Hz)")
        ax[2].set_title("PSD ($\mathrm{%s/\sqrt{Hz}}$)" % self.spectrum.units,
                        size="medium")
        
        # Plot the sweep
        self.sweep.ax = ax[1]
        self.sweep.plot()
        ax[1].set_ylabel("")
        ax[1].set_title("DC SQUID Signal ($\Phi_o$)",
                        size="medium")

    def run(self, save_appendedpath = ''):
        self.istuned = self.tune_squid()
        if self.istuned == False:
            return False
        self.preamp.filter = (1, 300000)
        self.squidarray.reset()
        self.spectrum = SQUIDSpectrum(self.instruments)
        self.spectrum.saa_status = self.squidarray.__dict__
        self.spectrum.run(save_appendedpath = save_appendedpath)
        plt.close()
        self.squidarray.sensitivity = "Medium"
        self.squidarray.reset()
        self.preamp.filter = (1, 300)
        self.preamp.gain = 1
        self.squidarray.reset()
        self.sweep = MutualInductance2(self.instruments,
                                       np.linspace(-1e-3, 1e-3, 1000),
                                       conversion = 1/1.44)
        self.sweep.saa_status = self.squidarray.__dict__
        self.sweep.run(save_appendedpath = save_appendedpath)
        plt.close()
        self.plot()
        plt.close()
        return True

    @staticmethod
    def __init__(self,
                 instruments,
                 squid_bias,
                 squid_tol = 100e-3,
                 aflux_tol = 10e-3,
                 sflux_offset = 0.0,
                 aflux_offset = 0.0):

class Array_Tune_Batch(Measurement):
    def __init__(self, 
                 instruments,
                 sbias = [0], 
                 aflux = [0], 
                 sflux = [0],
                 squid_tol = 100e-3, 
                 aflux_tol = 10e-3, 
                 save_appendedpath = ''):
        '''
        live plotting only plots the first element of sflux, all of 
        sbias and aflux
        '''
        
        super(Array_Tune_Batch, self).__init__(instruments=instruments)

        self.instruments = instruments
        self.sbias = sbias
        self.aflux = sflux
        self.sflux = sflux
        self.squid_tol = squid_tol
        self.aflux_tol = aflux_tol
        self.save_appendedpath = save_appendedpath

    def do(liveplot = True)

        # Take 1 arraytune scan
        # use that to create the entire structure
        # That way, if it fails, it will fail at the beginning

        # things to save:
        # spectrum:
        #   1 copy of f (Hz)
        #   n copies of psdave * conversion (phi_0)
        # mutalinductance2:
        #   n copies of Vsrc / Rbias (Amps)
        #   n copies of Vmeas * conversion (phi_0)
        # array_tune:
        #   n copies of char[1] (test signal, V)
        #   n copies of char[2] (saa signal,  V)
        # n copies of sbias, aflux, sflux


        # name of nparrays to be saved in this object
        # order follows all the "n copies" of stuff in the above
        # comment
        self.savenames = ['spectrum_psd', 'sweep_fcIsrc', 'sweep_sresp',
                           'char_testsig', 'char_saasig']
        first = True
        index = 0
        maxlen = len(self.sbias)*len(self.aflux)*len(self.sflux)
        self.spectrum_f = np.array([])
        self.lockparams = np.zeros( (maxlen, 3))
        self.success    = np.zeros(maxlen) # zero is false

        sbindex = 0


        for sb in self.sbias:
            for af in self.aflux:
                plottingindex = [] # for live plotting
                plottingindex.append(index)
                for sf in self.sflux:
                    [index, first] = self._tunesave(index,sb,af,sf,first)

            if liveplot:
                [noise_z, lin_z] = self.plot_makeline(plottingindex)
                self.plotting_z[0][sbindex, :] = noise_z
                self.plotting_z[1][sbindex, :] = lin_z
                self.plot_live()

            sbindex += 1 
        

    def _tunesave(self, index, sb, af, sf, first):

        self.lockparams[index] = np.array([sb, af, sf])

        at = ArrayTune(self.instruments, squid_bias=sb, 
                       squid_tol = self.squid_tol,
                       aflux_tol = self.aflux_tol,
                       sflux_offset = sf,
                       aflux_offset = af)
        locked = at.run(save_appendedpath=self.save_appendedpath)

        if not locked:
            index += 1
            return [index, first]

        self.success[index] = 1

        # what to save
        tosave = [np.array(at.spectrum.psdAve * at.spectrum.conversion),
                  np.array(at.sweep.Vsrc / at.sweep.Rbias),
                  np.array(at.sweep.Vmeas * at.sweep.conversion),
                  np.array(at.char[1]), 
                  np.array(at.char[2])
                 ]

        if first: # do not know size until you try
            Array_Tune_Batch._makestruct(self, tosave, self.savenames)
            self.spectrum_f = np.array(at.spectrum.f)
            first = False

        Array_Tune_Batch._savetostruct(self, tosave, self.savenames, index)
        index += 1

        return [index, first]


    def plot_makeline(self, indexes):
        n_l_z = np.full(self.aflux, np.nan)
        l_l_z = np.full(self.aflux, np.nan)

        index_fstart = np.argmin(abs(self.spectrum_f - 100))
        index_fstop  = np.argmin(abs(self.spectrum_f - 1000))

        for n,l,i in zip(n_l_z, l_l_z, indexes):
            if not self.success[i]:
                continue
            n = np.sqrt(np.mean(np.square(
                    (self.spectrum_psd[i])[index_fstart, index_fstop])))
            [p,v] = np.polyfit(self.sweep_fcIsrc[i], self.sweep_sresp[i],1,
                             covar=True)
            l = v[0]
        return [n_l_z, l_l_z]

    def setup_plots():
        # 2D live plot:
        #   squid bias vs array flux vs noise
        #   squid bias vs array flux vs measure of linearity
        # 1D plot:
        #   waterfall (offset by array flux) of squid characteristic

        self.fig, self.axes = plt.subplots(1,3)
        self.axes = list(self.axes.flatten())

        self.plotting_z = [
                np.full((len(self.aflux), len(self.sbias)), np.nan),
                np.full((len(self.aflux), len(self.sbias)), np.nan)
                          ]
        self.images = []
        self.cbars  = []
        for ax, data, cbarlabel in zip(
                [self.axes[0], self.axes[1]], 
                self.plotting_z,
                [r'noise ($\phi_0/\sqrt{Hz}$)', 
                 r'linearity (covar of fit)']
                ):
            masked_data = np.ma.array(data mask=np.isnan(data))
            image = ax.imshow(masked_data, self.cmap, origin='lower',
                              excent=[self.sbias.min(), self.sbias.max(),
                                      self.aflux.min(), self.aflux.max()])

            d = max_axes_locatable(ax)
            cax = d.append_axes('right', size=.1, pad=.1)
            cbar = plt.colorbar(image, cax=cax)
            cbar.set_label(cbarlabel, rotation=270, labelpad=12)

            ax.set_xlabel('S bias (uA)')
            ax.set_ylabel('A flux offset (a.u.)')

            self.cbars.append(cbar)
            self.images.append(image)


    def plot_live():
        for image,cbar,data in zip(self.images,self.cbars,self.plotting_z):
            masked_data = np.ma.array(data mask=np.isnan(data))
            image.set_data(masked_data)
            cbar.set_clim([masked_data.min(), masked_data.max()])
            cbar.draw_all()
        self.fig.canvas.draw()
        plt.pause(.001)



    def plot():
        pass


    @classmethod
    def _makestruct(obj, tosave, savenames, maxlen):
        for name, item in zip(savenames, tosave):
            setattr(obj, name, np.zeros( (maxlen, len(item))))

    @classmethod
    def _savetostruct(obj, tosave, savenames, index):
        for name, item in zip(savenames, tosave):
            try:
                getattr(obj, name)[index] = item
            except:
                print(['Cannot set {0} of len {1}'.format(item, len(item))
                       ' to {2} expecting len {3}'.format(name, 
                           len(getattr(obj, name)[index]))
                      ])

                    
                                   

