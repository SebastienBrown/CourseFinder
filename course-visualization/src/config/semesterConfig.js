// export const AVAILABLE_SEMESTERS = ['2223F', '2223S', '2324F', '2324S'];
export const AVAILABLE_SEMESTERS = ['0910F', '0910S', '1011F', '1011S', '1112F', '1112S', '1213F', '1213S', '1314F', '1314S', '1415F', '1415S', '1516F', '1516S', '1617F', '1617S', '1718F', '1718S', '1819F', '1819S', '1920F', '1920S', '2021F', '2021J', '2021S', '2122F', '2122J', '2122S', '2223F', '2223S', '2324F', '2324S', '2425F', '2425S'];
export const CURRENT_SEMESTER = "2324S";

export function getSemesterDataPaths(semester) {
  return {
    courseDetails: `/amherst_courses_all.json`,
    tsneCoords: `/precomputed_tsne_coords_all.json`,
    similarityData: `/output_similarity_all.json`,
  };
}