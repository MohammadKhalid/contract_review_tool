/**
 * Temporary client-side storage for file snapshots during a Polar purchase flow.
 * Uses IndexedDB so we can survive full page navigations/redirects that Polar
 * performs on checkout success (which destroy all in-memory React state + File objects).
 *
 * Keys are the real checkoutId (after create-checkout) or a short-lived temp key
 * (generated on buy click before we have the checkoutId).
 *
 * Entries are short-lived and aggressively pruned.
 */

const DB_NAME = 'contract-review-temp-purchases';
const STORE_NAME = 'pending-files';
const DB_VERSION = 1;

interface StoredFileRecord {
  name: string;
  type: string;
  lastModified: number;
  data: ArrayBuffer;
  storedAt: number;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      return reject(new Error('IndexedDB not available'));
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error('IndexedDB blocked'));
  });
}

async function withStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest<T> | Promise<T>
): Promise<T> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, mode);
    const store = tx.objectStore(STORE_NAME);

    const request = fn(store);

    tx.oncomplete = () => {
      // For cases where fn returned a request, the result is already resolved below
    };
    tx.onerror = () => reject(tx.error);

    if (request instanceof IDBRequest) {
      request.onsuccess = () => resolve(request.result as T);
      request.onerror = () => reject(request.error);
    } else {
      // If fn returned a promise (rare), handle it
      Promise.resolve(request).then(resolve).catch(reject);
    }
  });
}

export async function storePendingFile(key: string, file: File): Promise<void> {
  try {
    const data = await file.arrayBuffer();
    const record: StoredFileRecord = {
      name: file.name,
      type: file.type,
      lastModified: file.lastModified,
      data,
      storedAt: Date.now(),
    };
    await withStore('readwrite', (store) => store.put(record, key));
  } catch (err) {
    // Non-fatal: fall back to "user will have to re-select" UX
    console.warn('[tempPurchaseFile] Failed to snapshot file for key', key, err);
  }
}

export async function loadAndReconstructFile(key: string): Promise<File | null> {
  try {
    const record = await withStore('readonly', (store) => store.get(key));
    if (!record) return null;

    const { name, type, lastModified, data } = record as StoredFileRecord;
    // Reconstruct a real File so FileUpload and analyzeContract treat it normally
    return new File([data], name, { type, lastModified });
  } catch (err) {
    console.warn('[tempPurchaseFile] Failed to load snapshot for key', key, err);
    return null;
  }
}

export async function deletePendingFile(key: string): Promise<void> {
  try {
    await withStore('readwrite', (store) => store.delete(key));
  } catch (err) {
    console.warn('[tempPurchaseFile] Failed to delete snapshot for key', key, err);
  }
}

export async function pruneOldPendingFiles(maxAgeMs = 30 * 60 * 1000): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const now = Date.now();

    const request = store.openCursor();
    request.onsuccess = () => {
      const cursor = request.result;
      if (cursor) {
        const record = cursor.value as StoredFileRecord;
        if (record.storedAt && now - record.storedAt > maxAgeMs) {
          cursor.delete();
        }
        cursor.continue();
      }
    };
    // tx will auto-commit
  } catch (err) {
    console.warn('[tempPurchaseFile] Prune failed', err);
  }
}

/** Clear all pending entries (used on full "New Analysis" reset). */
export async function clearAllPendingFiles(): Promise<void> {
  try {
    await withStore('readwrite', (store) => store.clear());
  } catch (err) {
    console.warn('[tempPurchaseFile] clearAll failed', err);
  }
}

// Convenience: call on app boot or reset for hygiene
export async function ensureCleaned(): Promise<void> {
  // Fire and forget
  pruneOldPendingFiles().catch(() => {});
}