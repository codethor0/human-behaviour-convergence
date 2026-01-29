'use client';

import { useEffect, useState } from 'react';

const styles = {
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    padding: '20px',
  },
  insight: {
    fontSize: '16px',
    lineHeight: '1.6',
    color: '#ffffff',
    marginBottom: '16px',
  },
  highlight: {
    color: '#00ff88',
    fontWeight: '600',
  },
  link: {
    color: '#0070f3',
    textDecoration: 'underline',
    cursor: 'pointer',
    fontSize: '14px',
  },
  timestamp: {
    fontSize: '12px',
    color: '#666666',
    marginTop: 'auto',
  },
};

export function InsightOfTheDay() {
  const [insight, setInsight] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const generateInsight = async () => {
      try {
        // This would call a backend service to generate insights
        // For now, use template-based insights
        const insights = [
          'Behavior Index shows <span style="color: #ffd700">moderate stress</span> across most regions, with <span style="color: #ff8800">California</span> showing elevated environmental factors.',
          'Economic stress indicators are <span style="color: #00ff88">stabilizing</span> after last week\'s volatility, suggesting improved market confidence.',
          'Mobility patterns indicate <span style="color: #ffd700">gradual recovery</span> in urban centers, with weekend activity returning to pre-pandemic levels.',
        ];

        const randomInsight = insights[Math.floor(Math.random() * insights.length)] ?? '';
        setInsight(randomInsight);
        setLoading(false);
      } catch (error) {
        console.error('Failed to generate insight:', error);
        setLoading(false);
      }
    };

    generateInsight();
    // Regenerate daily at midnight
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    const msUntilMidnight = tomorrow.getTime() - now.getTime();

    const timeout = setTimeout(generateInsight, msUntilMidnight);
    return () => clearTimeout(timeout);
  }, []);

  if (loading) {
    return <div style={{ color: '#ffffff' }}>Generating insight...</div>;
  }

  return (
    <div style={styles.container}>
      <div
        style={styles.insight}
        dangerouslySetInnerHTML={{ __html: insight }}
      />
      <a
        href="/forecast-overview"
        style={styles.link}
      >
        View detailed forecast →
      </a>
      <div style={styles.timestamp}>
        Updated {new Date().toLocaleDateString()}
      </div>
    </div>
  );
}
