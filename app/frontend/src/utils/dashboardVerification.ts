/**
 * Dashboard Visibility Verification Utilities
 * 
 * This module provides utilities to verify that all Grafana dashboards
 * are properly rendered and visible on the main page.
 */

export interface DashboardInfo {
  uid: string;
  title: string;
  isVisible: boolean;
  hasError: boolean;
  errorMessage?: string;
}

/**
 * Verify that all expected dashboards are present in the DOM
 */
export function verifyDashboardsInDOM(): DashboardInfo[] {
  if (typeof window === 'undefined') {
    return [];
  }

  const dashboardEmbeds = document.querySelectorAll('[data-testid^="dashboard-embed-"]');
  const results: DashboardInfo[] = [];

  dashboardEmbeds.forEach((element) => {
    const testId = element.getAttribute('data-testid');
    const uid = testId?.replace('dashboard-embed-', '') || '';
    
    const _iframe = element.querySelector('iframe');
    const errorDiv = element.querySelector('[style*="f8d7da"]'); // Error div background color
    
    const isVisible = 
      element instanceof HTMLElement &&
      element.offsetHeight > 0 &&
      element.offsetWidth > 0 &&
      window.getComputedStyle(element).display !== 'none' &&
      window.getComputedStyle(element).visibility !== 'hidden' &&
      window.getComputedStyle(element).opacity !== '0';
    
    const hasError = errorDiv !== null;
    const errorMessage = hasError ? errorDiv?.textContent || 'Unknown error' : undefined;
    
    const titleElement = element.querySelector('h2');
    const title = titleElement?.textContent || uid;

    results.push({
      uid,
      title,
      isVisible,
      hasError,
      errorMessage,
    });
  });

  return results;
}

/**
 * Count total dashboards rendered
 */
export function countRenderedDashboards(): number {
  if (typeof window === 'undefined') {
    return 0;
  }
  return document.querySelectorAll('[data-testid^="dashboard-embed-"]').length;
}

/**
 * Check if a specific dashboard is visible
 */
export function isDashboardVisible(uid: string): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  
  const element = document.querySelector(`[data-testid="dashboard-embed-${uid}"]`);
  if (!element || !(element instanceof HTMLElement)) {
    return false;
  }
  
  const style = window.getComputedStyle(element);
  return (
    element.offsetHeight > 0 &&
    element.offsetWidth > 0 &&
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.opacity !== '0'
  );
}
