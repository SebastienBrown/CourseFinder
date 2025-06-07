/************************************************************************************
** Department/field panel data construction, descriptives and analysis 
* AUTHOR: Harufumi Nakazawa
* Created: Jun 2, 2025

************************************************************************************/

global path = "/Users/hnaka24/engaging/CourseFinder/analysis/"
global data = "${path}data/"
global output = "${path}output/"

************************************************************************************
* Import course count
import delimited "${data}course_counts_by_semester_dept.csv", clear

	* Conjoin departments
	replace dept = "MUSI" if dept == "MUSL"
	replace dept = "CLAS" if dept == "LATI" | dept == "GREE"
	replace dept = "SWAG" if dept == "WAGS"
	replace dept = "ASLC" if dept == "ARAB" | dept == "CHIN" | dept == "JAPA"

	* Clean Sample
	drop if length(dept) != 4
	drop if dept == "FYSE" | dept == "COLQ" | dept == "BRUS" | dept == "MELL" | dept == "KENA"
	
	* Add breadth requirement field
	gen field = .
	replace field = 1 if inlist(dept, "ARCH", "ARHA", "MUSI", "MUSL", "THDA")
	replace field = 2 if inlist(dept, "AAPI", "AMST", "ASLC", "BLST", "CLAS", "EDST", "ENGL", "ENST", "EUST")
	replace field = 2 if inlist(dept, "FAMS", "FREN", "GERM", "HIST", "LJST", "LLAS", "PHIL", "RELI")
	replace field = 2 if inlist(dept, "RUSS", "SPAN", "SWAG")
	replace field = 3 if inlist(dept, "ASTR", "BCBP", "BIOL", "CHEM", "COSC")
	replace field = 3 if inlist(dept, "GEOL", "MATH", "NEUR", "PHYS", "STAT")
	replace field = 4 if inlist(dept, "ANTH", "ECON", "POSC", "PSYC", "SOCI")
	replace field = 5 if inlist(dept, "MIXD")

	label define fields 1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences" 5 "Cross-listed"
	label values field fields

	* Proper year
	replace year = floor(year / 100) + 2000

* Collapse to year level
preserve
	collapse course_count, by(field dept year)
	drop if year > 2023
	drop if dept == "MIXD"
	
	tempfile coursecount
	save `coursecount'
restore

************************************
*** Descriptives
* Make continuous year variable
replace year = year + 0.5 if strpos(semester, "F") > 0 & year != 2020 & year != 2021
replace year = year + 0.66 if strpos(semester, "F") > 0 & (year == 2020 | year == 2021)
replace year = year + 0.33 if strpos(semester, "S") > 0 & (year == 2020 | year == 2021)

* Plot Count
collapse (sum) course_count, by(field year)

twoway line course_count year if field == 1, lcolor(blue) ///
|| line course_count year if field == 2, lcolor(red) ///
|| line course_count year if field == 3, lcolor(green) ///
|| line course_count year if field == 4, lcolor(orange) ///
|| line course_count year if field == 5, lcolor(purple) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences" 5 "Cross-listed") position(6) rows(1)) ///
    title("Number of Courses by Field, 2009-2026") ///
    ytitle("Number of Courses") ///
    xtitle("Year") graphregion(margin(l=2 r=8 t=2 b=2) color(white))
graph export "${output}coursecount_year.pdf", replace

************************************
* Import enrollment data
import delimited "${data}enrollment_data_csv.txt", varnames(1) clear

reshape long v, i(department dept) j(year)
rename v enrollment
replace year = year + 2000

drop if year < 2009

* Merge
sort dept year
merge 1:1 dept year using `coursecount'

* Make balanced panel and fill in zeroes
gen nonzero = (enrollment != . & course_count != .)
bysort dept: egen balanced = min(nonzero)

replace enrollment = 0 if enrollment == .
replace course_count = 0 if course_count == .

drop _merge

egen deptcode = group(dept)

forval i = 1/4 {
	gen course_`i' = (field == `i') * course_count
}

save "${data}cleaned_dept_panel.dta", replace

************************************
*** Descriptives

* Plot enrollment count
preserve
collapse (sum) enrollment course_count, by(field year)

twoway line enrollment year if field == 1, lcolor(blue) ///
|| line enrollment year if field == 2, lcolor(red) ///
|| line enrollment year if field == 3, lcolor(green) ///
|| line enrollment year if field == 4, lcolor(orange) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences") position(6) rows(1)) ///
    title("Enrollment Count by Field, 2009-2023") ///
    ytitle("Enrollment Count") ///
    xtitle("Year") graphregion(margin(l=2 r=8 t=2 b=2) color(white))
graph export "${output}enrollcount_year.pdf", replace

* Plot enrollment share
bysort year: egen total_enrollment = total(enrollment)
gen enroll_share = enrollment / total_enrollment
	
twoway line enroll_share year if field == 1, lcolor(blue) ///
|| line enroll_share year if field == 2, lcolor(red) ///
|| line enroll_share year if field == 3, lcolor(green) ///
|| line enroll_share year if field == 4, lcolor(orange) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences") position(6) rows(1)) ///
    title("Enrollment Share by Field, 2009-2023") ///
    ytitle("Enrollment Share") ///
    xtitle("Year") graphregion(margin(l=2 r=8 t=2 b=2) color(white))
graph export "${output}enrollshare_year.pdf", replace

* Plot class size
gen classsize = enrollment / course_count

twoway line enroll_share year if field == 1, lcolor(blue) ///
|| line enroll_share year if field == 2, lcolor(red) ///
|| line enroll_share year if field == 3, lcolor(green) ///
|| line enroll_share year if field == 4, lcolor(orange) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences") position(6) rows(1)) ///
    title("Average Class Size by Field, 2009-2023") ///
    ytitle("Average Class Size") ///
    xtitle("Year") graphregion(margin(l=2 r=8 t=2 b=2) color(white))
graph export "${output}classsize_year.pdf", replace

restore

************************************************************************************
*** Regression Analysis
gen classsize = enrollment / course_count

*** Main specification
reghdfe enrollment course_count, absorb(dept year) vce(robust)
reghdfe enrollment course_count, absorb(dept year field#c.year) vce(robust)
reghdfe enrollment course_count, absorb(dept year deptcode#c.year) vce(robust)
reghdfe enrollment course_count if balanced == 1, absorb(dept year deptcode#c.year) vce(robust)

reghdfe classsize course_count, absorb(dept year) vce(robust)
reghdfe classsize course_count, absorb(dept year field#c.year) vce(robust)
reghdfe classsize course_count, absorb(dept year deptcode#c.year) vce(robust)
reghdfe classsize course_count if balanced == 1, absorb(dept year deptcode#c.year) vce(robust)

*** Bin scatter
	* Residualize enrollment
	reghdfe enrollment, absorb(dept year deptcode#c.year) resid(enroll_resid)

	* Residualize classsize
	reghdfe classsize, absorb(dept year deptcode#c.year) resid(classsize_resid)
	
	* Residualize course_count
	reghdfe course_count, absorb(dept year deptcode#c.year) resid(course_resid)

	binscatter enroll_resid course_resid, linetype(lfit) n(50) ///
		xtitle("Residualized Course Count") ///
		ytitle("Residualized Enrollment") ///
		title("Binned Scatterplot: Enrollment on Course Count")
	graph export "${output}enrollcount_coursecount_binscatter.pdf", replace

	binscatter classsize_resid course_resid, linetype(lfit) n(50) ///
		xtitle("Residualized Course Count") ///
		ytitle("Residualized Class Size") ///
		title("Binned Scatterplot: Class Size on Course Count")
	graph export "${output}classsize_coursecount_binscatter.pdf", replace

*** Heterogeneity by field
reghdfe enrollment course_count course_2-course_4, absorb(dept year) vce(robust)
reghdfe enrollment course_count course_2-course_4, absorb(dept year deptcode#c.year) vce(robust)

reghdfe classsize course_count course_2-course_4, absorb(dept year) vce(robust)
reghdfe classsize course_count course_2-course_4, absorb(dept year deptcode#c.year) vce(robust)
