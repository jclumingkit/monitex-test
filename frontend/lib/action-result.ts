export type ActionResult<T> =
  | { data: T; error: null }
  | { data: null; error: string };

export const unwrapActionResult = <T>(result: ActionResult<T>): T => {
  if (result.error !== null) throw new Error(result.error);

  return result.data;
};
