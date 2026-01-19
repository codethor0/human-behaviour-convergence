// SPDX-License-Identifier: PROPRIETARY
/**
 * Shared hook for loading regions across /forecast, /playground, /live.
 *
 * Simplified: Direct fetch on mount with module-level cache for subsequent mounts.
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
let fetchPromise: Promise<Region[]> | null = null;

export function useRegions(): UseRegionsResult {
  const [regions, setRegions] = useState<Region[]>(cachedRegions || []);
  const [loading, setLoading] = useState<boolean>(!cachedRegions);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    // Clear cache
    cachedRegions = null;
    fetchPromise = null;
    setLoading(true);
    setError(null);
    setRegions([]);
  }, []);

  useEffect(() => {
    // If we have cached data, use it immediately
    if (cachedRegions) {
      setRegions(cachedRegions);
      setLoading(false);
      return;
    }

    // If there's already a fetch in progress, reuse it
    if (fetchPromise) {
      fetchPromise
        .then((data) => {
          setRegions(data);
          setLoading(false);
        })
        .catch((e) => {
          setError(e instanceof Error ? e.message : 'Failed to load regions');
          setLoading(false);
        });
      return;
    }

    // Start a new fetch
    setLoading(true);
    fetchPromise = fetchRegions()
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
        setRegions(data);
        setError(null);
        setLoading(false);
        
        return data;
      })
      .catch((e) => {
        const errorMessage = e instanceof Error ? e.message : 'Failed to load regions';
        setError(errorMessage);
        setRegions([]);
        setLoading(false);
        throw e;
      });
  }, []); // Run once on mount

  return {
    regions,
    loading,
    error,
    reload,
  };
}
