// SPDX-License-Identifier: PROPRIETARY
/**
 * Shared hook for loading regions across /forecast, /playground, /live.
 *
 * Features:
 * - Fetches once and caches in memory (module-level singleton)
 * - Manages loading/error state
 * - Provides reload() for retry
 * - Avoids duplicate network calls
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchRegions, Region } from '../lib/api';

interface UseRegionsResult {
  regions: Region[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

// Module-level cache for regions (shared across all hook instances)
let cachedRegions: Region[] | null = null;
let cachePromise: Promise<Region[]> | null = null;
let cacheError: string | null = null;

export function useRegions(): UseRegionsResult {
  const [regions, setRegions] = useState<Region[]>(cachedRegions || []);
  const [loading, setLoading] = useState<boolean>(!cachedRegions && !cacheError);
  const [error, setError] = useState<string | null>(cacheError);

  const reload = useCallback(() => {
    // Clear cache to force fresh fetch
    cachedRegions = null;
    cachePromise = null;
    cacheError = null;

    setLoading(true);
    setError(null);
    setRegions([]);

    // Start new fetch
    const fetchPromise = fetchRegions()
      .then((data) => {
        // Validate response
        if (!Array.isArray(data)) {
          throw new Error(`Invalid response format: expected array, got ${typeof data}`);
        }

        if (data.length === 0) {
          throw new Error('Regions endpoint returned empty array');
        }

        // Update cache
        cachedRegions = data;
        cachePromise = null;
        cacheError = null;

        // Update state
        setRegions(data);
        setLoading(false);
        setError(null);

        return data;
      })
      .catch((e: unknown) => {
        const errorMessage = e instanceof Error
          ? e.message
          : 'Failed to load regions';

        // Update cache error
        cacheError = errorMessage;
        cachePromise = null;

        // Update state
        setError(errorMessage);
        setLoading(false);
        setRegions([]);

        throw e;
      });

    cachePromise = fetchPromise;
  }, []);

  useEffect(() => {
    // If we have cached data, use it immediately
    if (cachedRegions) {
      setRegions(cachedRegions);
      setLoading(false);
      setError(null);
      return;
    }

    // If there's already a fetch in progress, wait for it
    if (cachePromise) {
      cachePromise
        .then((data) => {
          setRegions(data);
          setLoading(false);
          setError(null);
        })
        .catch(() => {
          // Error already handled in reload, just set state
          setError(cacheError);
          setLoading(false);
          setRegions([]);
        });
      return;
    }

    // Otherwise, start a new fetch
    reload();
  }, [reload]);

  return {
    regions,
    loading,
    error,
    reload,
  };
}
