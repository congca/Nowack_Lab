import visa, atexit, time, numpy as np
from tabulate import tabulate
from .instrument import Instrument

_time_constant_values = [10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000]
_sensitivity_options = [
2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
50e-3, 100e-3, 200e-3, 500e-3, 1]
_reserve_options = ['High Reserve', 'Normal', 'Low Noise']


class SR830(Instrument):
    '''
    Instrument driver for SR830, modified from Guen's squidpy driver
    '''
    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address

        self.time_constant_options = {
                "10 us": 0,
                "30 us": 1,
                "100 us": 2,
                "300 us": 3,
                "1 ms": 4,
                "3 ms": 5,
                "10 ms": 6,
                "30 ms": 7,
                "100 ms": 8,
                "300 ms": 9,
                "1 s": 10,
                "3 s": 11,
                "10 s": 12,
                "30 s": 13,
                "100 s": 14,
                "300 s": 15,
                "1 ks": 16,
                "3 ks": 17,
                "10 ks": 18,
                "30 ks": 19
            }


    def __getstate__(self):
        self._save_dict = {"sensitivity": self.sensitivity,
                          "frequency": self.frequency,
                          "amplitude": self.amplitude,
                          "time_constant": self.time_constant,
                          "reserve": self.reserve,
                          "gpib_address": self.gpib_address,
                          "X": self.X,
                          "Y": self.Y,
                          "R": self.R,
                          "theta": self.theta}
        return self._save_dict


    def __setstate__(self, state):
        state['_sensitivity'] = state.pop('sensitivity')
        state['_frequency'] = state.pop('frequency')
        state['_amplitude'] = state.pop('amplitude')
        state['_time_constant'] = state.pop('time_constant')
        state['_reserve'] = state.pop('reserve')
        state['_X'] = state.pop('X')
        state['_Y'] = state.pop('Y')
        state['_R'] = state.pop('R')
        state['_theta'] = state.pop('theta')

        self.__dict__.update(state)


    @property
    def sensitivity(self):
        '''Get the lockin sensitivity'''
        self._sensitivity = _sensitivity_options[int(self.ask('SENS?'))]
        return self._sensitivity

    @sensitivity.setter
    def sensitivity(self, value):
        '''Set the sensitivity'''
        if value > 1:
            value = 1
        index = abs(np.array([v - value  if (v - value)>=0 else -100000 for v in _sensitivity_options])).argmin() #finds sensitivity just above input
        good_value = _sensitivity_options[index]

        self.write('SENS%d' %_sensitivity_options.index(good_value))

    @property
    def amplitude(self):
        '''Get the output amplitude'''
        self._amplitude = float(self.ask('SLVL?'))
        return self._amplitude

    @amplitude.setter
    def amplitude(self, value):
        '''Set the amplitude.'''
        if value < 0.004:
            value = 0.004
        if value > 5:
            value = 5
        self.write('SLVL %s' %value)

    @property
    def frequency(self):
        self._frequency = float(self.ask('FREQ?'))
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        self.write('FREQ %s' %value)

    @property
    def X(self):
        self._X = float(self.ask('OUTP?1'))
        return self._X

    @property
    def Y(self):
        self._Y = float(self.ask('OUTP?2'))
        return self._Y

    @property
    def R(self):
        self._R = float(self.ask('OUTP?3'))
        return self._R

    @property
    def theta(self):
        self._theta = float(self.ask('OUTP?4'))
        return self._theta

    @property
    def time_constant(self):
        options = {self.time_constant_options[key]: key for key in self.time_constant_options.keys()}
        self._time_constant = _time_constant_values[int(self.ask('OFLT?'))]
        #return options[int(self.ask('OFLT?'))]
        return self._time_constant

    @time_constant.setter
    def time_constant(self, value):
        if type(value) is str:
            if value in list(self.time_constant_options.keys()):
                index = self.time_constant_options[value]
            else:
                raise Exception('Must choose allowed time constant or input as float in units of seconds!')
        elif type(value) in (float, int):
            if value < 10e-6:
                value = 10e-6
            index = abs(np.array([value - v  if (value-v)>=0 else -100000 for v in _time_constant_values])).argmin() #finds time constant just below input
            good_value = _time_constant_values[index]

        self.write('OFLT %s' %index)

    @property
    def reserve(self):
        i = int(self.ask('RMOD?'))
        self._reserve = _reserve_options[i]
        return self._reserve

    @reserve.setter
    def reserve(self, value):
        i = _reserve_options.index(value)
        self.write('RMOD%i' %i)

    def ask(self, cmd):
        self.init_visa()
        out = self._visa_handle.ask(cmd)
        time.sleep(0.1)
        self.close()
        return out

    def ac_coupling(self):
        self.write('ICPL0')

    def auto_gain(self):
        self.write('AGAN')
        time.sleep(5) # let it finish

    def auto_phase(self):
        self.write('APHS')
        time.sleep(5) # let it finish

    def dc_coupling(self):
        self.write('ICPL1')

    def init_visa(self):
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'
        self._visa_handle.write('OUTX 1') #1=GPIB

    def get_all(self):
        table = []
        for name in ['sensitivity', 'amplitude', 'frequency', 'time_constant']:
            table.append([name, getattr(self, name)])
        snapped = self.ask('SNAP?1,2,3,4')
        snapped = snapped.split(',')
        table.append(['X', snapped[0]])
        table.append(['Y', snapped[1]])
        table.append(['R', snapped[2]])
        table.append(['theta', snapped[3]])
        return tabulate(table, headers = ['Parameter', 'Value'])

    def set_out(self, chan, param):
        """ set output on channel [1,2] to parameter [Ch1:['R','X'],Ch2:['Y','theta']]"""
        if chan == 1:
            if param not in ('R','X'):
                raise Exception('Cannot display %s on Channel 1!!' %param)
        elif chan == 2:
            if param not in ('Y','theta'):
                raise Exception('Cannot display %s on Channel 1!!' %param)
        else:
            raise Exception('Channel only 1 or 2!')

        if param in ('X', 'Y'):
            self.write('DDEF%i,0,0' %chan)
            self.write('FPOP%i,0' %chan)
        else:
            self.write('DDEF%i,1,0' %chan)
            self.write('FPOP%i,0' %chan)

    def convert_output(self, value):
        if not np.isscalar(value):
            value = np.array(value)
            return np.array(value/10*self.sensitivity) # will give actual output in volts, since output is scaled to 10 V == sensitivity
        return value/10*self.sensitivity

    def close(self):
        self._visa_handle.close()
        del(self._visa_handle)

    def write(self, cmd):
        self.init_visa()
        self._visa_handle.write(cmd)
        self.close()

if __name__ == '__main__':
    lockin = SR830('GPIB::09::INSTR')
    #print(lockin.time_constant)
    #lockin.auto_phase()
    print(lockin.get_all())
    #print(lockin.time_constant)

    #lockin.auto_gain()

    # lockin.auto_phase() # test this
