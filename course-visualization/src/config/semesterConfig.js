export const CURRENT_SEMESTER = 'all'; // Change this as needed

export function getSemesterDataPaths(semester) {
  return {
    courseDetails: `amherst_courses_${semester}.json`,
    tsneCoords: `precomputed_tsne_coords_${semester}.json`,
//     similarityData: `output_similarity_${semester}.json`,
  };
}