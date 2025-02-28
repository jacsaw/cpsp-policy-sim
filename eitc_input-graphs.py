

import pandas as pd
import matplotlib.pyplot as plt

df = pd.DataFrame()

# set income range over which to graph in increments of $500
df["Income"] = range(0, 42000, 500)

def eitc_credit(income):
    if income < phase_out_threshold:
        return min([income*phase_in_rate, eitc_max])
    else:
        po = (eitc_max - (income - phase_out_threshold)*phase_out_rate)
        if po > 0:
            return po
        else:
            return 0

def eitc_check_inputs(max_credit, phase_in_rate, phase_out_threshold):
    if max_credit/phase_in_rate < phase_out_threshold:
        raise ValueError("max credit too (%s) low for given phase in rate (%s) and threshold (%s)" % (max_credit, phase_in_rate, phase_out_threshold))  
    else:
        return True

#eitc in current law for 0 kids mfj
phase_in_rate = 0.0765
eitc_max = 632
phase_out_rate = .0765
phase_out_threshold = 17250


eitc_check_inputs(eitc_max, phase_in_rate, phase_out_threshold)
# the first simulation
df["Law"] = df["Income"].apply(lambda x: eitc_credit(x))

phase_in_rate = 0.2
eitc_max = 1000
phase_out_rate = .0765
phase_out_threshold = 40000
df["Alt1"] = df["Income"].apply(lambda x: eitc_credit(x))

phase_in_rate = 1.0
eitc_max = 1000
phase_out_rate = .0765
phase_out_threshold = 30000

df["Alt2"] = df["Income"].apply(lambda x: eitc_credit(x))

phase_in_rate = .0765
eitc_max = 2000
phase_out_rate = .0765
phase_out_threshold = 17250
eitc_check_inputs(eitc_max, phase_in_rate, phase_out_threshold)
df["max credit no pi adj"] = df["Income"].apply(lambda x: eitc_credit(x))

# plot the data
ax = df.plot(x="Income", y="Law", kind="line")
df.plot(x="Income", y="Alt1", kind="line", ax=ax, linestyle="--")
df.plot(x="Income", y="Alt2", kind="line", ax=ax, linestyle=":")
df.plot(x="Income", y="max credit no pi adj", kind="line", ax=ax, linestyle="-.")
plt.show()
