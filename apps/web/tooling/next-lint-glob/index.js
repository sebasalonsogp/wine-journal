import path from "node:path";
import { globSync as tinyGlobSync } from "tinyglobby";

// Only the pinned Next lint plugin's getRootDirs call is supported. Fail loudly
// if an upstream upgrade adds another use rather than silently changing linting.
export function globSync(pattern, options) {
  if (
    typeof pattern !== "string" ||
    options?.onlyDirectories !== true ||
    Object.keys(options).some((key) => key !== "onlyDirectories")
  ) {
    throw new Error("Review Next lint glob compatibility before changing its usage.");
  }
  // fast-glob preserves absolute patterns; tinyglobby otherwise returns relative
  // paths, including unusable cross-drive paths on Windows. Normalize dir suffixes.
  return tinyGlobSync(pattern, {
    onlyDirectories: true,
    expandDirectories: false,
    absolute: path.isAbsolute(pattern),
  }).map((directory) => directory.replace(/\/$/, "") || "/");
}
