export const AVAILABLE_SEMESTERS = ['2223F', '2223S', '2324F', '2324S'];
export const CURRENT_SEMESTER = "2324F";

export function getSemesterDataPaths(semester) {
  return {
    courseDetails: `/amherst_courses_all.json`,
    tsneCoords: `/precomputed_tsne_coords_all.json`,
    similarityData: `/output_similarity_all.json`,
  };
}