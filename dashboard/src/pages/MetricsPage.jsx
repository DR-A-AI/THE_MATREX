import React from 'react';
import { 
  CircularGaugeComponent, AxesDirective, AxisDirective, PointersDirective, PointerDirective, RangesDirective, RangeDirective, AnnotationsDirective, AnnotationDirective
} from '@syncfusion/ej2-react-circulargauge';
import { 
  ChartComponent, SeriesCollectionDirective, SeriesDirective, Inject, SplineSeries, DateTime, Legend, Tooltip 
} from '@syncfusion/ej2-react-charts';

export default function MetricsPage() {
  const chartData = [
    { x: new Date(2026, 5, 9, 6, 0), y: 100 },
    { x: new Date(2026, 5, 9, 6, 5), y: 95 },
    { x: new Date(2026, 5, 9, 6, 10), y: 98 },
    { x: new Date(2026, 5, 9, 6, 15), y: 100 }
  ];

  const primaryXAxis = { valueType: 'DateTime', title: 'Time', majorGridLines: { width: 0 }, labelStyle: { color: '#00f3ff' }, titleStyle: { color: '#00f3ff' } };
  const primaryYAxis = { title: 'Token Usage / Sec', minimum: 0, maximum: 200, labelStyle: { color: '#00f3ff' }, titleStyle: { color: '#00f3ff' } };

  return (
    <div className="flex-1 glass-panel p-6 flex flex-col gap-6 overflow-y-auto">
      <h2 className="text-2xl font-bold hologram-text mb-2 uppercase tracking-widest border-b border-[rgba(0,243,255,0.3)] pb-2">
        Sovereign Telemetry & Metrics
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Failsafe Stability Gauge */}
        <div className="glass-panel p-4 flex flex-col items-center">
          <h3 className="text-lg text-[#00f3ff] mb-4">Failsafe Stability Score</h3>
          <CircularGaugeComponent id="stability-gauge" background='transparent' theme='FabricDark' width='100%' height='250px'>
            <AxesDirective>
              <AxisDirective startAngle={210} endAngle={150} minimum={0} maximum={100} radius='80%' 
                lineStyle={{ width: 0 }} 
                majorTicks={{ width: 0 }} 
                minorTicks={{ width: 0 }}
                labelStyle={{ font: { color: '#00f3ff', fontFamily: 'Inter' } }}>
                <PointersDirective>
                  <PointerDirective value={98} radius='60%' color='#00f3ff' pointerWidth={8} cap={{ radius: 7, color: '#00f3ff' }} needleTail={{ length: '18%', color: '#00f3ff' }} />
                </PointersDirective>
                <RangesDirective>
                  <RangeDirective start={0} end={70} color='rgba(255,0,0,0.5)' radius='80%' startWidth={20} endWidth={20} />
                  <RangeDirective start={70} end={90} color='rgba(255,255,0,0.5)' radius='80%' startWidth={20} endWidth={20} />
                  <RangeDirective start={90} end={100} color='rgba(0,243,255,0.6)' radius='80%' startWidth={20} endWidth={20} />
                </RangesDirective>
              </AxisDirective>
            </AxesDirective>
          </CircularGaugeComponent>
        </div>

        {/* Network & Agent Status */}
        <div className="glass-panel p-4 flex flex-col gap-4 justify-center">
           <h3 className="text-lg text-[#00f3ff] border-b border-[rgba(0,243,255,0.3)] pb-2">Matrix Node Status</h3>
           <div className="flex justify-between items-center bg-[rgba(2,10,23,0.8)] p-3 rounded">
             <span className="text-[#00f3ff]">ZMQ Neural Bus</span>
             <span className="text-green-400 font-bold">ONLINE</span>
           </div>
           <div className="flex justify-between items-center bg-[rgba(2,10,23,0.8)] p-3 rounded">
             <span className="text-[#00f3ff]">Aegis Guardrails</span>
             <span className="text-green-400 font-bold">ACTIVE</span>
           </div>
           <div className="flex justify-between items-center bg-[rgba(2,10,23,0.8)] p-3 rounded">
             <span className="text-[#00f3ff]">Librarian Crawler</span>
             <span className="text-yellow-400 font-bold">INDEXING</span>
           </div>
        </div>
      </div>

      {/* Token Usage Chart */}
      <div className="glass-panel p-4 w-full">
        <h3 className="text-lg text-[#00f3ff] mb-4">Token Consumption Rate (Live)</h3>
        <ChartComponent id="token-chart" primaryXAxis={primaryXAxis} primaryYAxis={primaryYAxis} background='transparent' theme='FabricDark' tooltip={{ enable: true }}>
          <Inject services={[SplineSeries, DateTime, Legend, Tooltip]} />
          <SeriesCollectionDirective>
            <SeriesDirective dataSource={chartData} xName='x' yName='y' type='Spline' name='Tokens / Sec' fill='#00f3ff' width={3} opacity={0.8} />
          </SeriesCollectionDirective>
        </ChartComponent>
      </div>

    </div>
  );
}
