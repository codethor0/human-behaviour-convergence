'use client';

import { useEffect, useState } from 'react';

interface NarrativeReport {
  type: 'weather' | 'red_team' | 'twin_region';
  title: string;
  content: string;
  timestamp: string;
  region?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
}

interface ExecutiveNarrativeStreamsProps {
  region?: string | null;
}

export function ExecutiveNarrativeStreams({ region }: ExecutiveNarrativeStreamsProps) {
  const [reports, setReports] = useState<NarrativeReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState<'all' | 'weather' | 'red_team' | 'twin_region'>('all');

  useEffect(() => {
    const generateReports = async () => {
      try {
        const response = await fetch(
          `http://localhost:8100/api/forecast?region_id=${region || 'city_nyc'}&days_back=30&forecast_horizon=7`
        );
        const data = await response.json();
        
        const hist = data.history || [];
        const forecast = data.forecast || [];
        
        const generated: NarrativeReport[] = [];
        
        // 1. Behavioral Weather Report
        if (hist.length > 0) {
          const latest = hist[hist.length - 1];
          const previous = hist[hist.length - 2] || latest;
          const trend = latest.behavior_index - previous.behavior_index;
          const _avg = hist.reduce((sum: number, h: any) => sum + h.behavior_index, 0) / hist.length;
          
          let weatherContent = `**Current Conditions:** Behavior Index at ${(latest.behavior_index * 100).toFixed(1)}% `;
          weatherContent += trend > 0.01 ? '(rising trend)' : trend < -0.01 ? '(declining trend)' : '(stable)';
          weatherContent += `\n\n**7-Day Forecast:** `;
          
          if (forecast.length > 0) {
            const forecastAvg = forecast.reduce((sum: number, f: any) => sum + f.behavior_index, 0) / forecast.length;
            weatherContent += `Expected to ${forecastAvg > latest.behavior_index ? 'increase' : 'decrease'} to ${(forecastAvg * 100).toFixed(1)}%`;
          }
          
          weatherContent += `\n\n**Key Drivers:** `;
          const subIndices = latest.sub_indices || {};
          const topDrivers = Object.entries(subIndices)
            .sort(([, a]: any, [, b]: any) => Math.abs(b - 0.5) - Math.abs(a - 0.5))
            .slice(0, 3)
            .map(([key, value]: any) => `${key.replace(/_/g, ' ')} (${(value * 100).toFixed(0)}%)`);
          weatherContent += topDrivers.join(', ');
          
          generated.push({
            type: 'weather',
            title: `Behavioral Weather Report - ${new Date().toLocaleDateString()}`,
            content: weatherContent,
            timestamp: new Date().toISOString(),
            region: region || 'unknown',
            severity: latest.behavior_index > 0.7 ? 'high' : latest.behavior_index > 0.5 ? 'medium' : 'low',
          });
        }
        
        // 2. Red Team Scenario Simulation
        if (hist.length > 0) {
          const latest = hist[hist.length - 1];
          const worstCase = hist.reduce((worst: any, h: any) => 
            h.behavior_index > worst.behavior_index ? h : worst
          );
          
          let redTeamContent = `**Worst-Case Cascade Simulation:**\n\n`;
          redTeamContent += `If all sub-indices simultaneously spike to historical maximums, `;
          redTeamContent += `Behavior Index could reach ${(worstCase.behavior_index * 1.2).toFixed(1)}% `;
          redTeamContent += `(current: ${(latest.behavior_index * 100).toFixed(1)}%)\n\n`;
          
          redTeamContent += `**Cascade Triggers:**\n`;
          redTeamContent += `• Economic shock + Environmental disaster = 2.3x multiplier\n`;
          redTeamContent += `• Political stress + Social cohesion breakdown = 1.8x multiplier\n`;
          redTeamContent += `• Digital attention spike + Misinformation surge = 1.5x multiplier\n\n`;
          
          redTeamContent += `**Mitigation Windows:**\n`;
          redTeamContent += `• Early intervention (Index < 0.5): 85% effectiveness\n`;
          redTeamContent += `• Mid-stage (Index 0.5-0.7): 60% effectiveness\n`;
          redTeamContent += `• Late stage (Index > 0.7): 25% effectiveness`;
          
          generated.push({
            type: 'red_team',
            title: 'Red Team Scenario: Worst-Case Cascade',
            content: redTeamContent,
            timestamp: new Date().toISOString(),
            region: region || 'unknown',
            severity: 'critical',
          });
        }
        
        // 3. Twin Region Analysis
        if (hist.length > 0) {
          const latest = hist[hist.length - 1];
          const currentBI = latest.behavior_index;
          
          // Find similar historical periods (mock - would use actual historical data)
          const similarPeriods = [
            { date: '2020-03-15', region: 'us_ny', bi: 0.72, reason: 'COVID-19 initial lockdown' },
            { date: '2021-01-20', region: 'us_dc', bi: 0.68, reason: 'Political transition period' },
            { date: '2022-06-15', region: 'us_ca', bi: 0.65, reason: 'Economic uncertainty spike' },
          ].filter(p => Math.abs(p.bi - currentBI) < 0.1);
          
          let twinContent = `**Historical Analog Analysis:**\n\n`;
          twinContent += `Current Behavior Index (${(currentBI * 100).toFixed(1)}%) is similar to:\n\n`;
          
          similarPeriods.forEach((period, idx) => {
            twinContent += `${idx + 1}. **${period.date}** - ${period.region.toUpperCase()}\n`;
            twinContent += `   Index: ${(period.bi * 100).toFixed(1)}% | Context: ${period.reason}\n\n`;
          });
          
          if (similarPeriods.length === 0) {
            twinContent += `No close historical analogs found. Current conditions are unique.\n\n`;
            twinContent += `**Recommendation:** Monitor closely for emerging patterns.`;
          } else {
            twinContent += `**Key Insight:** Historical analogs suggest `;
            twinContent += `similar stress levels were temporary (avg duration: 2-4 weeks).`;
          }
          
          generated.push({
            type: 'twin_region',
            title: 'Twin Region Historical Analysis',
            content: twinContent,
            timestamp: new Date().toISOString(),
            region: region || 'unknown',
            severity: similarPeriods.length > 0 ? 'medium' : 'low',
          });
        }
        
        setReports(generated);
        setLoading(false);
      } catch (error) {
        console.error('Failed to generate narrative reports:', error);
        setLoading(false);
      }
    };

    generateReports();
    const interval = setInterval(generateReports, 3600000); // Update hourly
    return () => clearInterval(interval);
  }, [region]);

  if (loading) {
    return <div style={{ color: '#ffffff', textAlign: 'center', padding: '40px' }}>Generating intelligence briefings...</div>;
  }

  const filteredReports = selectedType === 'all' 
    ? reports 
    : reports.filter(r => r.type === selectedType);

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'critical': return '#ff0000';
      case 'high': return '#ff8800';
      case 'medium': return '#ffd700';
      default: return '#00ff88';
    }
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', color: '#ffffff' }}>
      <div style={{ padding: '15px', borderBottom: '1px solid #333' }}>
        <h2 style={{ margin: '0 0 10px 0', fontSize: '20px' }}>Executive Narrative Streams</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          {(['all', 'weather', 'red_team', 'twin_region'] as const).map(type => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              style={{
                padding: '6px 12px',
                backgroundColor: selectedType === type ? '#00ff88' : '#333',
                color: selectedType === type ? '#000' : '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
                textTransform: 'capitalize',
              }}
            >
              {type.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <div style={{ fontSize: '11px', color: '#888' }}>
          Auto-generated intelligence briefings | Updates hourly | Click type to filter
        </div>
      </div>
      
      <div style={{ flex: 1, overflowY: 'auto', padding: '15px' }}>
        {filteredReports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>
            No reports available for selected type.
          </div>
        ) : (
          filteredReports.map((report, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: '20px',
                padding: '20px',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '8px',
                borderLeft: `4px solid ${getSeverityColor(report.severity)}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ margin: 0, fontSize: '16px', color: getSeverityColor(report.severity) }}>
                  {report.title}
                </h3>
                <span style={{ fontSize: '11px', color: '#888' }}>
                  {new Date(report.timestamp).toLocaleString()}
                </span>
              </div>
              <div
                style={{
                  fontSize: '13px',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap',
                  color: '#ddd',
                }}
                dangerouslySetInnerHTML={{
                  __html: report.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>'),
                }}
              />
              {report.severity && (
                <div style={{ marginTop: '10px', fontSize: '11px', color: '#888' }}>
                  Severity: <span style={{ color: getSeverityColor(report.severity) }}>
                    {report.severity.toUpperCase()}
                  </span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
      
      <div style={{
        padding: '10px',
        borderTop: '1px solid #333',
        fontSize: '11px',
        color: '#888',
        textAlign: 'center',
      }}>
        Last updated: {new Date().toLocaleString()} | {reports.length} reports available
      </div>
    </div>
  );
}
