cd "C:\Users\smc2246\Box\Sophie Collyer (smc2246) Personal Folder\Gates"

preserve
import delimited "EITC parameters.csv", clear

keep if year == 2023
mkmat nkids eitc_pirate eitc_mininc eitc_max eitc_porate *_shoh ///
	eitc_invtinc_cap, mat(shoh)
mkmat nkids eitc_pirate eitc_mininc eitc_max eitc_porate *_mfj ///
	eitc_invtinc_cap, mat(mfj)

mat list shoh
mat list mfj
restore
 


********************************************************************************
* Import data shared with VIGET  
******************************************************************************** 

import delimited "C:\Users\smc2246\Box\Gates Platform\Data\Sample dataset for Viget\augmented_cps_2024.csv", clear 
merge 1:1 hh_id person_num using "C:\Users\smc2246\Box\Sophie Collyer (smc2246) Personal Folder\Gates\additional eitc variables.dta"

*merge 1:1 hh_id person_num using "C:\Users\smc2246\Box\Sophie Collyer (smc2246) Personal Folder\Gates\additional eitc variables2.dta"

* Key inputs into the EITC calculation*****************************************
* Filing type 
  gen shoh_file = (single_filer==1 | hoh_filer==1) & tax_dep==0
  gen mfj_file = (joint_filer==1)
  
* Age of filer 1 (and 2 in case of joint filers)
	cap drop *spouse*_age
 	gen filer1_age = age if primary_filer ==1 
	gen filer2_age = age if primary_filer ==0 & joint_filer==1 

	bysort year tax_id: egen tu_filer1_age = max(filer1_age)
	bysort year tax_id: egen tu_filer2_age = max(filer2_age)

* For each tax unit, identify number of qualifying dependents 
	*identify dependents
	cap drop dep_eitc
	gen dep_eitc = 0
		replace dep_eitc = 1 if tax_dep>0 & age<19 
		replace dep_eitc = 1 if tax_dep>0 & inrange(age, 19, 23) & ///
				a_hscol!=0 & a_ftpt!=0
		replace dep_eitc = 1 if tax_dep>0 & pedisdrs==1 & ///
				pedisear==1 & pediseye==1 & pedisout==1 & ///
				pedisphy==1 & pedisrem==1
	
	*count qualifying dependents at tax unit level
	cap drop tu_depeitc
	bysort year tax_id: egen tu_depeitc = total(dep_eitc)
	
	*cap the number of qualifying dependents
	recode tu_depeitc (3/max=3)
	
			
* Tax unit level earnings, excluding dependents
	foreach var of varlist r_p_wagesal r_p_selfemp r_p_farmself agi fica_se {
	cap drop *`var'_nodep
	gen `var'_nodep = `var' if tax_dep==0 & (primary_filer==1|joint_filer==1 & primary_filer==0)
	bysort hh_id tax_id: egen tu_`var'_nodep = total(`var'_nodep)
	  }
	
* Total earned income for EITC, excl. dependents and at tax unit level
	cap drop tu_pearn_eitc 		// earned income for EITC
	gen tu_pearn_eitc = tu_r_p_wagesal_nodep + tu_r_p_selfemp_nodep + tu_r_p_farmself_nodep - (tu_fica_se_nodep / 2)
	recode tu_pearn_eitc (min/0=0)
	
* Get schedule E income for investment income calculation
	gen sched_e = cond(inlist(oi_off, 7, 8), oi_val, 0)  

* Investment income
	cap drop *pinvt*
	gen pinvt = r_p_incint + r_p_div 
	replace pinvt = pinvt + cap_val if cap_val>=0 
	replace pinvt = pinvt + rnt_val + sched_e if (rnt_val + sched_e)>=0
	gen pinvt_nodep = pinvt if tax_dep==0
	bysort year tax_id: egen tu_pinvt_eitc = total(pinvt_nodep)

	
* Calculate the EITC ***********************************************************

	*Identify population possibly eligible 
	cap drop eitc_possible
	gen eitc_possible=0
	foreach stat in shoh  mfj {
	foreach num of numlist 1/4 {
	replace eitc_possible = tu_pearn_eitc<`stat'[`num', 7] & ///
						    tu_agi_nodep < `stat'[`num', 7] & ///
						    tu_pinvt_eitc<=`stat'[`num', 9] ///
						    if `stat'_file==1 & tu_depeitc==`num'-1  & tu_pearn_eitc>0 
	
 		 
	}
	}
							
	replace eitc_possible = 0 if (age < 25 |age >= 65) & tu_depeitc==0 & shoh_file==1
	replace eitc_possible = 0 if  mfj_file==1 & tu_filer1_age<25 & ///
			tu_filer2_age<25 & tu_depeitc==0
	replace eitc_possible = 0 if mfj_file==1  & tu_filer1_age>=65 & ///
			tu_filer2_age>=65  & tu_depeitc==0
	ta eitc_possible
	
	cap drop eitc_cpsp*
	gen eitc_cpsp_earn = .
	gen eitc_cpsp_agi = .
	
	foreach stat in shoh mfj {
	foreach num of numlist 1/4 {
		
	*EITC based on earned income 	
	replace eitc_cpsp_earn = ///
			min(`stat'[`num', 2]*tu_pearn_eitc, `stat'[`num', 4]) if ///
		   `stat'_file==1 & tu_depeitc==`num'-1 & ///
		   eitc_possible==1 &  tu_pearn_eitc<`stat'[`num', 6] 
	
	
	replace eitc_cpsp_earn = ///
			max(0, `stat'[`num', 4] - (`stat'[`num', 5] * ///
		   (tu_pearn_eitc-`stat'[`num', 6]))) if `stat'_file==1 & ///
		   tu_depeitc==`num'-1 & tu_pearn_eitc > `stat'[`num', 6] & ///
		   eitc_possible==1  
	
	
	
	
	*EITC based on AGI   
	replace eitc_cpsp_agi = ///
			max(0, `stat'[`num', 4] - (`stat'[`num', 5] * ///
		    (tu_agi_nodep-`stat'[`num', 6]))) if `stat'_file==1 & ///
		    tu_depeitc==`num'-1 & tu_agi_nodep > `stat'[`num', 6] & ///
		    eitc_possible==1  & (tu_agi_nodep>=`stat'[`num', 8])   
		}
		}
		
	*clean up values 	
	
	foreach x in earn agi {
	replace eitc_cpsp_`x' = round(eitc_cpsp_`x', 1) // round
	replace eitc_cpsp_`x' = 0 if primary_filer!=1  // get on the line of primary filer only 
	recode eitc_cpsp_`x' (min/0=0)
 	}
	
* Get final EITC credit value 
	cap drop eitc_cpsp
	gen eitc_cpsp = 0
	replace eitc_cpsp = min(eitc_cpsp_earn,eitc_cpsp_agi) if ///
			eitc_cpsp_agi>0 & eitc_cpsp_earn>0
	replace eitc_cpsp = max(eitc_cpsp_earn, eitc_cpsp_agi) if ///
			eitc_cpsp_agi==0 | eitc_cpsp_earn==0
	
* Aggregate at tax unit level and review correlation with census values	
	cap drop tu_eitc_cpsp*
	bysort year tax_id: egen tu_eitc_cpsp = total(eitc_cpsp)

 	cap drop tu_eit_cred
	bysort year tax_id: egen tu_eit_cred = total(r_p_eitc)
	
	corr tu_eitc_cpsp tu_eit_cred 
	gen dif_eitc=tu_eitc_cpsp -tu_eit_cred 
	
	