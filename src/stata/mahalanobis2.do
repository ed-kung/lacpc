clear all
set more off


* 0) Setup

cd "../../intermediate_data/cpc"


local filename1 "ologit.main_effects.mahalanobis.csv"
local filename2 "ologit.marginal_effects.mahalanobis.csv"

import delimited using "working_file.csv", clear varnames(1) encoding(UTF-8)

* current independent variable
local distance mahalanobis

local ctrls_cluster i.cluster
local ctrls_complex agenda_perplexity agenda_order num_agenda_items consent_calendar n__support n__oppose
local ctrls_district cd2 cd1 cd3 cd4 cd5 cd6 cd7 cd8 cd9 cd10 cd11 cd12 cd13 cd14 cd15
local ctrls_sfx sfx_1a sfx_administrativeadjustments sfx_cu sfx_db sfx_hca sfx_hd sfx_mcup sfx_otheraffordablehousingpublic sfx_otherdevelopmentreview sfx_otherlanduseentitlements sfx_otherother sfx_spp sfx_spr sfx_toc


* 1) Fit the model as controls increase
estimates clear

ologit project_result `distance', vce(robust)
est store m0

* ologit project_result `distance' `ctrls_cluster', vce(robust)
* est store m1

ologit project_result `distance' `ctrls_cluster' `ctrls_complex', vce(robust)
est store m2

ologit project_result `distance' `ctrls_cluster' `ctrls_complex' `ctrls_district', vce(robust)
est store m3

ologit project_result `distance' `ctrls_cluster' `ctrls_complex' `ctrls_district' `ctrls_sfx', vce(robust)
est store m4


* 2) Marginal effects for each outcome, store each
margins, dydx(*) predict(outcome(0)) post
est store me0

ologit project_result `distance' `ctrls_cluster' `ctrls_complex' `ctrls_district' `ctrls_sfx', vce(robust)

margins, dydx(*) predict(outcome(1)) post
est store me1

ologit project_result `distance' `ctrls_cluster' `ctrls_complex' `ctrls_district' `ctrls_sfx', vce(robust)

margins, dydx(*) predict(outcome(2)) post
est store me2


* 3) Save results

capture which esttab
if _rc {
    di as error "esttab not installed. Installing..."
    ssc install estout, replace
}

* Write one table: replace once, then append columns

esttab m0 m2 m3 m4 using "`filename1'", replace ///
    se b(3)                           ///
    star(* 0.1 ** 0.05 *** 0.01)     ///
    stats(N r2_p p, fmt(0 3 3)        ///
          labels("Obs" "Pseudo R-squared" "Prob > chi2")) ///
    title("Ologit coeffs")

esttab me2 me1 me0 using "`filename2'", append ///
    se b(3)                                   ///
    star(* 0.1 ** 0.05 *** 0.01)             ///
    stats(N, fmt(0) labels("Obs"))            ///
    mtitles("ME: outcome 2" "ME: outcome 1" "ME: outcome 0")
	
* 4) Robustness

* A) Baseline (few controls)
reg project_result `distance' `ctrls_cluster' `ctrls_complex', vce(robust)
scalar b0  = _b[`distance']
scalar r20 = e(r2)

* B) Kitchen sink
reg project_result `distance' `ctrls_cluster' `ctrls_complex' `ctrls_district' `ctrls_sfx', vce(robust)
scalar b1  = _b[`distance']
scalar r21 = e(r2)

* C) Oster / AET-style sensitivity
scalar rmax = 1.3*r21

* δ that sets beta* = 0
scalar delta0 = (b1*(r21 - r20)) / ((b0 - b1)*(rmax - r21))

* Bias-adjusted beta* at δ = 1 (selection on unobs = selection on obs)
scalar beta_star_d1 = b1 - 1*(b0 - b1)*((rmax - r21)/(r21 - r20))

display "delta for beta*=0: " %9.4f delta0
display "beta* at delta=1: "  %9.4f beta_star_d1

quietly capture log close _all
exit 0

