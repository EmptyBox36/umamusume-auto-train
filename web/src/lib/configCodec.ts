import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from "lz-string";

// very small non-crypto checksum to catch paste errors
const djb2 = (s: string) => {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h) ^ s.charCodeAt(i);
  return (h >>> 0).toString(36).slice(0, 6); // 6 chars
};

type Versioned<T> = { v: 1; data: T }; // bump v when config shape changes

export function encodeConfig<T>(cfg: T): string {
  const payload: Versioned<T> = { v: 1, data: cfg };
  const json = JSON.stringify(payload);
  const packed = compressToEncodedURIComponent(json);
  const sum = djb2(json);
  return `${packed}.${sum}`; // "<compressed>.<checksum>"
}

export function decodeConfig<T>(code: string): T {
  const idx = code.lastIndexOf(".");
  if (idx < 0) throw new Error("Invalid code");
  const packed = code.slice(0, idx);
  const sum = code.slice(idx + 1);

  const json = decompressFromEncodedURIComponent(packed);
  if (!json) throw new Error("Corrupted or incompatible code");
  if (djb2(json) !== sum) throw new Error("Checksum mismatch");

  const parsed = JSON.parse(json) as Versioned<T>;
  if (parsed.v !== 1) throw new Error("Unsupported version");
  return parsed.data;
}