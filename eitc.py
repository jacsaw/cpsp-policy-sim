""" 
"""

from pydoc import describe

import pandas as pd

cps = (
    pd.read_csv("augmented_cps_2024.csv")
)

# stata
# import delimited "augmented_cps_2024.csv", clear  # unsure what clear is in stata
cpsadd = pd.read_csv("additional eitc variables_12062024.csv")

# print(cpsadd.describe())

# stata
# merge 1:1 hh_id person_num using "additional eitc variables.dta"
cpsnew = cps.merge(cpsadd, on = ["hh_id", "person_num"], how = "left", suffixes = ("","_1",))
# print(cpsnew.columns)
# print(cpsnew.loc[0])

#check values the same post merge in on instance
# print(cpsnew.loc[0]["oi_off"], cpsnew.loc[0]["oi_off_1"])

# stata script
#  gen shoh_file = (single_filer==1 | hoh_filer==1) & tax_dep==0
#  gen mfj_file = (joint_filer==1)

cpsnew["shoh_file"] = cpsnew.apply(lambda row: 1 if ((row["single_filer"] == 1 or row["hoh_filer"] == 1) and row["tax_dep"] == 0) else 0, axis=1)
cpsnew["mfj_file"] = cpsnew.apply(lambda row: 1 if row["joint_filer"] == 1 else 0, axis=1)

# stata
# * Age of filer 1 (and 2 in case of joint filers)
# 	cap drop *spouse*_age
#  	gen filer1_age = age if primary_filer ==1
# 	gen filer2_age = age if primary_filer ==0 & joint_filer==1

cpsnew["filer1_age"] = cpsnew.apply(lambda row: row["age"] if row["primary_filer"] == 1 else None, axis=1)
cpsnew["filer2_age"] = cpsnew.apply(lambda row: row["age"] if (row["primary_filer"] == 0 and row["joint_filer"] == 1) else None, axis=1)

# stata
#   bysort year tax_id: egen tu_filer1_age = max(filer1_age)
# 	bysort year tax_id: egen tu_filer2_age = max(filer2_age)

cpsnew["tu_filer1_age"] = cpsnew.groupby(["year", "tax_id"])["filer1_age"].transform('max')
cpsnew["tu_filer2_age"] = cpsnew.groupby(["year", "tax_id"])["filer2_age"].transform('max')

# stata
#       gen dep_eitc = 0
# 		replace dep_eitc = 1 if tax_dep>0 & age<19
# 		replace dep_eitc = 1 if tax_dep>0 & inrange(age, 19, 23) & ///
# 				a_hscol!=0 & a_ftpt!=0
# 		replace dep_eitc = 1 if tax_dep>0 & pedisdrs==1 & ///
# 				pedisear==1 & pediseye==1 & pedisout==1 & ///
# 				pedisphy==1 & pedisrem==1

cpsnew["dep_eitc"]= cpsnew.apply(lambda row: 1 if (
            (row["tax_dep"] > 0 ) and
            ((row["age"] < 19) or
            (row["age"] < 24 and row["a_hscol"] != 0 and row["a_ftpt"] != 0) or
            # why is this only 1 if all of these are true? must have each column marked as 1
            (row["pedisdrs"] == 1 and row["pedisear"] == 1 and row["pediseye"] == 1 and row["pedisout"] == 1 and row["pedisphy"] == 1 and row["pedisrem"])
            ))
        else 0, axis=1
    )

# stata
# *count qualifying dependents at tax unit level
# 	cap drop tu_depeitc
# 	bysort year tax_id: egen tu_depeitc = total(dep_eitc)

cpsnew["tu_depeitc"] = cpsnew.groupby(["year", "tax_id"])["dep_eitc"].transform('sum')

# stata
# *cap the number of qualifying dependents
# 	recode tu_depeitc (3/max=3)

cpsnew["tu_depeitc"] = cpsnew.apply(lambda row: 3 if row["tu_depeitc"] > 3 else row["tu_depeitc"], axis=1)

# * Tax unit level earnings, excluding dependents
# 	foreach var of varlist r_p_wagesal r_p_selfemp r_p_farmself agi fica_se {
# 	cap drop *`var'_nodep
# 	gen `var'_nodep = `var' if tax_dep==0 & (primary_filer==1|joint_filer==1 & primary_filer==0) # <-- the bool here may be incorrect depending on how stata reads the bool
# 	bysort hh_id tax_id: egen tu_`var'_nodep = total(`var'_nodep)
# 	  }
for var in ["r_p_wagesal", "r_p_selfemp", "r_p_farmself", "agi", "fica_se"]:
    cpsnew[f"{var}_nodep"] = cpsnew.apply(lambda row: row[var] if (row["tax_dep"] == 0 and (row["primary_filer"] == 1 or (row["joint_filer"] == 1 and row["primary_filer"] == 0))) else 0, axis=1)
    cpsnew[f"tu_{var}_nodep"] = cpsnew.groupby(["hh_id", "tax_id"])[f"{var}_nodep"].transform("sum")

# * Total earned income for EITC, excl. dependents and at tax unit level
# 	cap drop tu_pearn_eitc 		// earned income for EITC
# 	gen tu_pearn_eitc = tu_r_p_wagesal_nodep + tu_r_p_selfemp_nodep + tu_r_p_farmself_nodep - (tu_fica_se_nodep / 2)
# 	recode tu_pearn_eitc (min/0=0)

cpsnew["tu_pearn_eitc"] = cpsnew.apply(lambda row: (row["tu_r_p_wagesal_nodep"] + row["tu_r_p_selfemp_nodep"] + row["tu_r_p_farmself_nodep"] - (row["tu_fica_se_nodep"] / 2)) if (row["tu_r_p_wagesal_nodep"] + row["tu_r_p_selfemp_nodep"] + row["tu_r_p_farmself_nodep"] - (row["tu_fica_se_nodep"] / 2))>0 else 0, axis=1)

# * Get schedule E income for investment income calculation
# 	gen sched_e = cond(inlist(oi_off, 7, 8), oi_val, 0)

cpsnew["sched_e"] = cpsnew.apply(lambda row: row["oi_val"] if row["oi_off"] in [7,8] else 0, axis=1 )

# * Investment income
# 	cap drop *pinvt*
# 	gen pinvt = r_p_incint + r_p_div
# 	replace pinvt = pinvt + cap_val if cap_val>=0
# 	replace pinvt = pinvt + rnt_val + sched_e if (rnt_val + sched_e)>=0
# 	gen pinvt_nodep = pinvt if tax_dep==0
# 	bysort year tax_id: egen tu_pinvt_eitc = total(pinvt_nodep)


cpsnew["pinvt"] = cpsnew.apply(
    lambda row: (row["r_p_incint"] + row["r_p_div"]),
axis=1)

cpsnew["pinvt"] = cpsnew.apply(
    lambda row: row["pinvt"] + row["cap_val"] if row["cap_val"] >=0 else row["pinvt"],
axis=1)

cpsnew["pinvt"] = cpsnew.apply(
    lambda row: row["pinvt"] + row["rnt_val"] + row["sched_e"]
        if (row["rnt_val"] + row["sched_e"] >=0)
        else row["pinvt"],
axis=1)

cpsnew["pinvt_nodep"] = cpsnew.apply(
    lambda row: row["pinvt"] if row["tax_dep"] == 0 else 0,
axis=1)

cpsnew["tu_pinvt_eitc"] = cpsnew.groupby(["year", "tax_id"])["pinvt_nodep"].transform("sum")

# Calculate EITC

# Get EITC parameters

eitc_params = pd.read_csv("EITC parameters.csv")
eitc_params = eitc_params[eitc_params["year"] == 2023]

common_columns = ["nkids", "eitc_pirate", "eitc_mininc", "eitc_max", "eitc_porate", "eitc_invtinc_cap"]
shoh = eitc_params[[*common_columns, *[c for c in eitc_params.columns if "_shoh" in c]]].reset_index()
mfj = eitc_params[[*common_columns, *[c for c in eitc_params.columns if "_mfj" in c]]].reset_index()


# 	*Identify population possibly eligible
# 	cap drop eitc_possible
# 	gen eitc_possible=0
# 	foreach stat in shoh  mfj {
# 	foreach num of numlist 1/4 {
# 	replace eitc_possible = tu_pearn_eitc<`stat'[`num', 7] & ///
# 						    tu_agi_nodep < `stat'[`num', 7] & ///
# 						    tu_pinvt_eitc<=`stat'[`num', 9] ///
# 						    if `stat'_file==1 & tu_depeitc==`num'-1  & tu_pearn_eitc>0
#
#
# 	}
# 	}


for i in range(0,4):
    cpsnew["eitc_possible"] = cpsnew[
        (cpsnew["shoh_file"] == 1) &
         (cpsnew["tu_depeitc"] == i) &
        (cpsnew["tu_pinvt_eitc"] > 0)].apply(
            lambda row:
                True if (
                    row["tu_pearn_eitc"] < shoh.loc[i][shoh.columns[6]] and
                    row["tu_agi_nodep"] < shoh.loc[i][shoh.columns[6]] and
                    row["tu_pinvt_eitc"] <= shoh.loc[i][shoh.columns[8]]
                ) else False, axis=1)
    cpsnew["eitc_possible"] = cpsnew[
        (cpsnew["mfj_file"] == 1) &
        (cpsnew["tu_depeitc"] == i) &
        (cpsnew["tu_pinvt_eitc"] > 0)].apply(
        lambda row:
        True if (
                row["tu_pearn_eitc"] < mfj.loc[i][mfj.columns[6]] and
                row["tu_agi_nodep"] < mfj.loc[i][mfj.columns[6]] and
                row["tu_pinvt_eitc"] <= mfj.loc[i][mfj.columns[8]]
        ) else False, axis=1)

# We can definitely make this and the above more efficient by selecting only eligible fields
# replace eitc_possible = 0 if (age < 25 |age >= 65) & tu_depeitc==0 & shoh_file==1

cpsnew["eitc_possible"] = cpsnew.apply(lambda row: False if ((row["age"] <25 or row["age"] >= 65) and row["tu_depeitc"] == 0 and row["shoh_file"] == 1 ) else row["eitc_possible"], axis=1)

# 	replace eitc_possible = 0 if  mfj_file==1 & tu_filer1_age<25 & ///
# 			tu_filer2_age<25 & tu_depeitc==0
# 	replace eitc_possible = 0 if mfj_file==1  & tu_filer1_age>=65 & ///
# 			tu_filer2_age>=65  & tu_depeitc==0

cpsnew["eitc_possible"] = cpsnew.apply(lambda row: False if (row["mfj_file"]==1 and row["tu_depeitc"]
            and ((row["tu_filer1_age"]<25
            and row["tu_filer2_age"] < 25)
            or (row["tu_filer1_age"] >= 65 and row["tu_filer2_age"] >= 65)))
else row["eitc_possible"], axis=1)

print(cpsnew.describe())
print(cpsnew["eitc_possible"].describe())
print(cpsnew["eitc_cpsp"].describe())


#
# foreach stat in shoh mfj {
# 	foreach num of numlist 1/4 {
#
# 	*EITC based on earned income
# 	replace eitc_cpsp_earn = ///
# 			min(`stat'[`num', 2]*tu_pearn_eitc, `stat'[`num', 4]) if ///
# 		   `stat'_file==1 & tu_depeitc==`num'-1 & ///
# 		   eitc_possible==1 &  tu_pearn_eitc<`stat'[`num', 6]

# this code removes the loop of the index for number of dependents and references it from each row
cpsnew["eitc_cpsp_earn"] = cpsnew.apply(
                        lambda row:
                                min( mfj.loc[row["tu_depeitc"]][mfj.columns[1]]*row["tu_pearn_eitc"],
                                     mfj.loc[row["tu_depeitc"]][mfj.columns[3]]
                                ) if (row["tu_pearn_eitc"] < mfj.loc[row["tu_depeitc"]][mfj.columns[5]] and
                                      row["mfj_file"] == 1 and
                                     row["eitc_possible"] == 1)
                                  else 0, axis=1)

cpsnew["eitc_cpsp_earn"] = cpsnew.apply(
                        lambda row:
                                min( shoh.loc[row["tu_depeitc"]][shoh.columns[1]]*row["tu_pearn_eitc"],
                                     shoh.loc[row["tu_depeitc"]][shoh.columns[3]]
                                ) if (row["tu_pearn_eitc"] < shoh.loc[row["tu_depeitc"]][shoh.columns[5]] and
                                      (row["shoh_file"] == 1) and
                                      (row["eitc_possible"] == 1)
                                      )
                                  else 0, axis=1)



# 	replace eitc_cpsp_earn = ///
# 			max(0, `stat'[`num', 4] - (`stat'[`num', 5] * ///
# 		   (tu_pearn_eitc-`stat'[`num', 6]))) if `stat'_file==1 & ///
# 		   tu_depeitc==`num'-1 & tu_pearn_eitc > `stat'[`num', 6] & ///
# 		   eitc_possible==1
#
cpsnew["eitc_cpsp_earn"] = cpsnew.apply(
    lambda row: max(0, mfj.loc[row["tu_depeitc"]][mfj.columns[3]] - (mfj.loc[row["tu_depeitc"]][mfj.columns[4]] * (row["tu_pearn_eitc"] - mfj.loc[row["tu_depeitc"]][mfj.columns[5]])))
    if (row["tu_pearn_eitc"] > mfj.loc[row["tu_depeitc"]][mfj.columns[5]] and
        (row["mfj_file"] == 1) and (row["eitc_possible"] == 1)
        ) else 0, axis=1)


# Note for all of these where something like 'shoh.columns[index]' is referenced
# these can be turned into the column name instead of the index
# also python is 0 indexed vs 1 indexed of stata, this numbered indexes are 1 less than the stata
cpsnew["eitc_cpsp_earn"] = cpsnew.apply(
    lambda row: max(0, shoh.loc[row["tu_depeitc"]][shoh.columns[3]] - (shoh.loc[row["tu_depeitc"]][shoh.columns[4]] * (row["tu_pearn_eitc"] - shoh.loc[row["tu_depeitc"]][shoh.columns[5]])))
    if (row["tu_pearn_eitc"] > shoh.loc[row["tu_depeitc"]][shoh.columns[5]] and (row["shoh_file"] == 1) and (row["eitc_possible"] == 1)) else 0, axis=1)


# 	*EITC based on AGI
# 	replace eitc_cpsp_agi = ///
# 			max(0, `stat'[`num', 4] - (`stat'[`num', 5] * ///
# 		    (tu_agi_nodep-`stat'[`num', 6]))) if `stat'_file==1 & ///
# 		    tu_depeitc==`num'-1 & tu_agi_nodep > `stat'[`num', 6] & ///
# 		    eitc_possible==1  & (tu_agi_nodep>=`stat'[`num', 8])
# 		}
# 		}

cpsnew["eitc_cpsp_agi"] = cpsnew.apply(
    lambda row: max(0, shoh.loc[row["tu_depeitc"]][shoh.columns[3]] - (shoh.loc[row["tu_depeitc"]][shoh.columns[4]] * (row["tu_agi_nodep"] - shoh.loc[row["tu_depeitc"]][shoh.columns[5]])))
    if (row["tu_agi_nodep"] > shoh.loc[row["tu_depeitc"]][shoh.columns[5]] and row["tu_agi_nodep"] >= shoh.loc[row["tu_depeitc"]][shoh.columns[7]] and (row["shoh_file"] == 1) and (row["eitc_possible"] == 1)) else 0, axis=1)

cpsnew["eitc_cpsp_agi"] = cpsnew.apply(
    lambda row: max(0, mfj.loc[row["tu_depeitc"]][mfj.columns[3]] - (mfj.loc[row["tu_depeitc"]][mfj.columns[4]] * (row["tu_agi_nodep"] - mfj.loc[row["tu_depeitc"]][mfj.columns[5]])))
    if (row["tu_agi_nodep"] > mfj.loc[row["tu_depeitc"]][mfj.columns[5]] and row["tu_agi_nodep"] >= mfj.loc[row["tu_depeitc"]][mfj.columns[7]] and (row["mfj_file"] == 1) and (row["eitc_possible"] == 1)) else 0, axis=1)

# *clean up values
#
# 	foreach x in earn agi {
# 	replace eitc_cpsp_`x' = round(eitc_cpsp_`x', 1) // round
# 	replace eitc_cpsp_`x' = 0 if primary_filer!=1  // get on the line of primary filer only
# 	recode eitc_cpsp_`x' (min/0=0)
#  	}

for val in ["earn", "agi"]:
    cpsnew[f"eitc_cpsp_{val}"].round(0)
    cpsnew[f"eitc_cpsp_{val}"] = cpsnew.apply(lambda row: 0 if row["primary_filer"] != 1 else row[f"eitc_cpsp_{val}"], axis=1)
    cpsnew.loc[cpsnew[f"eitc_cpsp_{val}"] < 0, f"eitc_cpsp_{val}"] = 0

# * Get final EITC credit value
# 	cap drop eitc_cpsp
# 	gen eitc_cpsp = 0
# 	replace eitc_cpsp = min(eitc_cpsp_earn,eitc_cpsp_agi) if ///
# 			eitc_cpsp_agi>0 & eitc_cpsp_earn>0
# 	replace eitc_cpsp = max(eitc_cpsp_earn, eitc_cpsp_agi) if ///
# 			eitc_cpsp_agi==0 | eitc_cpsp_earn==0


cpsnew["eitc_cpsp"] = cpsnew.apply(lambda row: min(row["eitc_cpsp_earn"], row["eitc_cpsp_agi"])
                                   if (row["eitc_cpsp_agi"] > 0 and row["eitc_cpsp_earn"] > 0)
                                   else (max(row["eitc_cpsp_earn"], row["eitc_cpsp_agi"]) if (row["eitc_cpsp_agi"] == 0 and row["eitc_cpsp_earn"] == 0) else 0), axis=1)


# * Aggregate at tax unit level and review correlation with census values
# 	cap drop tu_eitc_cpsp*
# 	bysort year tax_id: egen tu_eitc_cpsp = total(eitc_cpsp)
#
cpsnew["tu_eitc_cpsp"] = cpsnew.groupby(["year", "tax_id"])["eitc_cpsp"].transform("sum")
#  	cap drop tu_eit_cred
# 	bysort year tax_id: egen tu_eit_cred = total(r_p_eitc)
#
cpsnew["tu_eit_cred"] = cpsnew.groupby(["year", "tax_id"])["r_p_eitc"].transform("sum")

# 	corr tu_eitc_cpsp tu_eit_cred
# 	gen dif_eitc=tu_eitc_cpsp -tu_eit_cred


cpsnew["diff_eitc"] = cpsnew.apply(lambda row: row["tu_eitc_cpsp"] - row["tu_eit_cred"], axis=1)

print(cpsnew["diff_eitc"].describe())


# looking into
rows_with_tax_id_90802 = cpsnew[cpsnew["tax_id"] == 90802]
print(rows_with_tax_id_90802)

import ipdb; ipdb.set_trace()


