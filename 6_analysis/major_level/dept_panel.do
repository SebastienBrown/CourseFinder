/************************************************************************************
** Department/field panel data construction, descriptives and analysis 
* AUTHOR: Harufumi Nakazawa
* Created: Jun 2, 2025

************************************************************************************/

global raw = "/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/1_raw/registrar/"
global data = "/Users/hnaka24/Dropbox (Personal)/AmherstCourses/data/2_intermediate/5_scores/"
global output = "/Users/hnaka24/Dropbox (Personal)/AmherstCourses/output/7_analysis/"

************************************************************************************
* Import course count
/* import delimited "${data}n_coursess_by_semester_major.csv", clear

	* Conjoin departments
	replace major = "MUSI" if major == "MUSL"
	replace major = "CLAS" if major == "LATI" | major == "GREE"
	replace major = "SWAG" if major == "WAGS"
	replace major = "ASLC" if major == "ARAB" | major == "CHIN" | major == "JAPA"
*/
	
import delimited "${data}major_scores_panel.csv", clear

	* Clean Sample
	drop if major == "FYSE" | major == "COLQ" | major == "BRUS" | major == "MELL" | major == "KENA"
	drop if major == "AAPI" // no enrollment
	
	* Add breadth requirement field
	gen field = .
	replace field = 1 if inlist(major, "ARCH", "ARHA", "MUSI", "MUSL", "THDA")
	replace field = 2 if inlist(major, "AAPI", "AMST", "ASLC", "BLST", "CLAS", "EDST", "ENGL", "ENST", "EUST")
	replace field = 2 if inlist(major, "FAMS", "FREN", "GERM", "HIST", "LJST", "LLAS", "PHIL", "RELI")
	replace field = 2 if inlist(major, "RUSS", "SPAN", "SWAG")
	replace field = 3 if inlist(major, "ASTR", "BCBP", "BIOL", "CHEM", "COSC")
	replace field = 3 if inlist(major, "GEOL", "MATH", "NEUR", "PHYS", "STAT")
	replace field = 4 if inlist(major, "ANTH", "ECON", "POSC", "PSYC", "SOCI")
	replace field = 5 if inlist(major, "MIXD")
	replace field = 6 if inlist(major, "ALL")

	label define fields 1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences" 5 "Cross-listed" 6 "ALL"
	label values field fields

	* Proper year
	gen year = substr(semester, 1, 4) if semester != "ALL"
	destring year, replace
	replace year = floor(year / 100) + 2000

* Collapse to year level
preserve
	collapse (sum) n_courses (mean) n_components avg_distance (max) max_distance, by(field major year)
	drop if year > 2023
	drop if major == "ALL"
	drop if semester == "ALL"
	drop if major == "MIXD"
	
	tempfile coursecount
	save `coursecount'
restore

************************************
*** Descriptives

********************
* Major rankings
********************
preserve
keep if semester == "ALL"
drop if major == "MIXD"
tempfile full_list
save `full_list', replace

* Only one component (many tied for the last place)
levelsof major if n_components == 1, local(onecomponent)

* Loop through your variables
local varlist "n_courses n_components avg_distance max_distance"
foreach var in `varlist' {
    
    use `full_list', clear
    gsort -`var'
    gen rank = _n
	local n_majors = _N
	
    keep if _n <= 5 | _n >= _N - 4
	gen value = `var'
	keep rank major value
	rename major major_`var'
	rename value `var'
	
    tempfile ranking_`var'
	save `ranking_`var'', replace
    
}

* Final dataset
clear
set obs `n_majors'
gen rank = _n
keep if _n <= 5 | _n >= _N - 4

foreach var in `varlist' {
	merge 1:1 rank using `ranking_`var'', nogen
}

replace major_n_components = "\multirow{5}{*}{`onecomponent'}" if _n == 6
replace major_n_components = "" if _n > 6

esttab using "${output}major_ranking.tex", cells("*") noobs nonumber unstack replace ///
	prehead()

restore


********************
* Time Trends by Field
********************
* Make continuous year variable and collapse by field
replace year = year + 0.5 if strpos(semester, "F") > 0 & year != 2020 & year != 2021
replace year = year + 0.66 if strpos(semester, "F") > 0 & (year == 2020 | year == 2021)
replace year = year + 0.33 if strpos(semester, "S") > 0 & (year == 2020 | year == 2021)

collapse (sum) n_courses (mean) n_components avg_distance (max) max_distance, by(field year)

* Plot # of courses
twoway line n_courses year if field == 1, lcolor(blue) ///
|| line n_courses year if field == 2, lcolor(red) ///
|| line n_courses year if field == 3, lcolor(green) ///
|| line n_courses year if field == 4, lcolor(orange) ///
|| line n_courses year if field == 5, lcolor(purple) ///
|| line n_courses year if field == 6, lcolor(black) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences" 5 "Cross-listed" 6 "ALL") position(6) rows(1)) ///
    title("Number of Courses by Field, 2009-2026") ///
    ytitle("Number of Courses") ///
    xtitle("Year") graphregion(margin(l=2 r=8 t=2 b=2) color(white))
graph export "${output}coursecount_year.pdf", replace

* Plot # of components
twoway line n_components year if field == 1, lcolor(blue) ///
|| line n_components year if field == 2, lcolor(red) ///
|| line n_components year if field == 3, lcolor(green) ///
|| line n_components year if field == 4, lcolor(orange) ///
|| line n_components year if field == 6, lcolor(black) yaxis(2) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences" 5 "ALL") ///
           position(6) rows(1)) ///
    title("Average Number of Components by Field, 2009-2026") ///
    ytitle("Avg Number of Components", axis(1)) ///
    ytitle("Avg Number of Components (ALL)", axis(2)) ///
    xtitle("Year") ///
    graphregion(margin(l=2 r=8 t=2 b=2) color(white))

* Plot avg distance
twoway line avg_distance year if field == 1, lcolor(blue) ///
|| line avg_distance year if field == 2, lcolor(red) ///
|| line avg_distance year if field == 3, lcolor(green) ///
|| line avg_distance year if field == 4, lcolor(orange) ///
|| line avg_distance year if field == 6, lcolor(black) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences" 5 "ALL") position(6) rows(1)) ///
    title("Average Pairwise Semantic Distance by Field, 2009-2026") ///
    ytitle("Average Pairwise Semantic Distance") ///
    xtitle("Year") graphregion(margin(l=2 r=8 t=2 b=2) color(white))

* Plot max distance
twoway line max_distance year if field == 1, lcolor(blue) ///
|| line max_distance year if field == 2, lcolor(red) ///
|| line max_distance year if field == 3, lcolor(green) ///
|| line max_distance year if field == 4, lcolor(orange) ///
|| line max_distance year if field == 6, lcolor(black) ///
    legend(order(1 "Arts" 2 "Humanities" 3 "Sciences" 4 "Social Sciences" 5 "ALL") position(6) rows(1)) ///
    title("Max Pairwise Semantic Distance by Field, 2009-2026") ///
    ytitle("Max Pairwise Semantic Distance") ///
    xtitle("Year") graphregion(margin(l=2 r=8 t=2 b=2) color(white))

	
************************************
* Import enrollment data
import delimited "${raw}enrollment_data_csv.txt", varnames(1) clear
rename dept major

reshape long v, i(department major) j(year)
rename v enrollment
replace year = year + 2000

drop if year < 2009

* Merge
sort major year
merge 1:1 major year using `coursecount'

* Make balanced panel and fill in zeroes
gen nonzero = !mi(enrollment, n_courses, n_components, avg_distance, max_distance)
bysort major: egen balanced = min(nonzero)

replace enrollment = 0 if enrollment == .
replace n_courses = 0 if n_courses == .

drop _merge

egen majorcode = group(major)

forval i = 1/4 {
	gen course_`i' = (field == `i') * n_courses
}

save "${data}cleaned_major_panel.dta", replace

************************************
*** Descriptives

* Plot enrollment count
preserve
collapse (sum) enrollment n_courses, by(field year)

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
gen classsize = enrollment / n_courses

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
*** Regression Analysis (# of courses)
gen classsize = enrollment / n_courses

*** Main specification
reghdfe enrollment n_courses, absorb(major year) vce(robust)
reghdfe enrollment n_courses, absorb(major year field#c.year) vce(robust)
reghdfe enrollment n_courses, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment n_courses if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

reghdfe classsize n_courses, absorb(major year) vce(robust)
reghdfe classsize n_courses, absorb(major year field#c.year) vce(robust)
reghdfe classsize n_courses, absorb(major year majorcode#c.year) vce(robust)
reghdfe classsize n_courses if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

*** Bin scatter
	* Residualize enrollment
	reghdfe enrollment, absorb(major year majorcode#c.year) resid(enroll_resid)

	* Residualize classsize
	reghdfe classsize, absorb(major year majorcode#c.year) resid(classsize_resid)
	
	* Residualize n_courses
	reghdfe n_courses, absorb(major year majorcode#c.year) resid(course_resid)

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
reghdfe enrollment n_courses course_2-course_4, absorb(major year) vce(robust)
reghdfe enrollment n_courses course_2-course_4, absorb(major year majorcode#c.year) vce(robust)

reghdfe classsize n_courses course_2-course_4, absorb(major year) vce(robust)
reghdfe classsize n_courses course_2-course_4, absorb(major year majorcode#c.year) vce(robust)

************************************************************************************
*** Regression Analysis (# of components and # of courses)

*******************
* Number of components
*******************
* Just # of components
reghdfe enrollment n_components, absorb(major year) vce(robust)
reghdfe enrollment n_components, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment n_components if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

* # of components and # of courses
reghdfe enrollment n_components n_courses, absorb(major year) vce(robust)
reghdfe enrollment n_components n_courses, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment n_components n_courses if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

*******************
* Avg distance
*******************
* Just avg distance
reghdfe enrollment avg_distance, absorb(major year) vce(robust)
reghdfe enrollment avg_distance, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment avg_distance if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

* Avg distance and # of courses
reghdfe enrollment avg_distance n_courses, absorb(major year) vce(robust)
reghdfe enrollment avg_distance n_courses, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment avg_distance n_courses if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

*******************
* Max distance
*******************
* Just max distance
reghdfe enrollment max_distance, absorb(major year) vce(robust)
reghdfe enrollment max_distance, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment max_distance if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

* Max distance and # of courses
reghdfe enrollment max_distance n_courses, absorb(major year) vce(robust)
reghdfe enrollment max_distance n_courses, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment max_distance n_courses if balanced == 1, absorb(major year majorcode#c.year) vce(robust)

*******************
* Everything
*******************
reghdfe enrollment n_components avg_distance max_distance n_courses, absorb(major year) vce(robust)
reghdfe enrollment n_components avg_distance max_distance n_courses, absorb(major year majorcode#c.year) vce(robust)
reghdfe enrollment n_components avg_distance max_distance n_courses if balanced == 1, absorb(major year majorcode#c.year) vce(robust)
