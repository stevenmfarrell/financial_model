document.addEventListener("DOMContentLoaded", async () => {
    try {
        // Fetch the data from the new API endpoint
        const response = await fetch('/api/data');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();

        if (data.error) {
            console.error("Error from server:", data.error);
            return;
        }

        // --- Simplified Color Palette ---
        const colors = {
            cash: { base: '#64748b', light: '#cbd5e1' },
            hsa: { base: '#d9254c', light: '#fda4af', dark: "#99122f" },
            roth: { base: '#a45ce6', light: '#c08bf7' },
            trad: { base: '#e8804a', light: '#fdba74' },
            brokerage: { base: '#3b72eb', light: '#6b92e8', dark: '#224dab' },
            income: { earned: '#059669', ss: '#10b981' },
            outflows: {
                taxes: '#000000',
                mortgage: '#917c61',
                spending: '#738576'
            }
        };

        const xLabels = data.years.map((year, i) => `${data.ages[i]}<br>${year}`);
        const tickIndices = data.years.map((_, i) => i).filter(i => i % 5 === 0);
        const tickVals = tickIndices.map(i => xLabels[i]);

        const commonLayout = {
            template: 'plotly_white',
            hovermode: 'x unified',
            margin: { l: 90, r: 30, t: 30, b: 50 },
            xaxis: {
                tickmode: 'array',
                tickvals: tickVals,
                ticktext: tickVals,
                automargin: true
            },
            yaxis: {
                automargin: true,
                tickformat: '$.2s',
                title: { standoff: 20 }
            }
        };

        const plotConfig = { responsive: true };

        // 1. Assets Chart
        Plotly.newPlot('assets_chart', [
            { x: xLabels, y: data.assets.hsa, name: 'HSA', type: 'bar', marker: { color: colors.hsa.base } },
            { x: xLabels, y: data.assets.traditional, name: 'Traditional', type: 'bar', marker: { color: colors.trad.base } },
            {
                x: xLabels, y: data.assets.roth_conversion, name: 'Roth (Conversion)', type: 'bar',
                marker: {
                    pattern: {
                        shape: '/', bgcolor: colors.roth.base, fgcolor: colors.trad.base,
                        fgopacity: 0.9, size: 8, solidity: 0.3
                    }
                }
            },
            { x: xLabels, y: data.assets.roth_basis, name: 'Roth (Basis)', type: 'bar', marker: { color: colors.roth.base } },
            { x: xLabels, y: data.assets.roth_growth, name: 'Roth (Growth)', type: 'bar', marker: { color: colors.roth.light } },
            { x: xLabels, y: data.assets.brokerage_basis, name: 'Brokerage (Basis)', type: 'bar', marker: { color: colors.brokerage.base } },
            { x: xLabels, y: data.assets.brokerage_growth, name: 'Brokerage (Growth)', type: 'bar', marker: { color: colors.brokerage.light } },
            { x: xLabels, y: data.assets.cash, name: 'Cash', type: 'bar', marker: { color: colors.cash.base } },
            { x: xLabels, y: data.assets.total, name: 'Total Liquid Assets', mode: 'lines', line: { width: 3, color: '#000' } }
        ], {
            ...commonLayout,
            barmode: 'stack',
            yaxis: { ...commonLayout.yaxis, title: 'Balance (Real $)' }
        }, plotConfig);

        // 2. Sources Chart
        Plotly.newPlot('sources_chart', [
            { x: xLabels, y: data.income.earned, name: 'Earned Income', type: 'bar', marker: { color: colors.income.earned } },
            { x: xLabels, y: data.income.ss, name: 'Social Security', type: 'bar', marker: { color: colors.income.ss } },
            { x: xLabels, y: data.withdrawals.trad, name: 'From Trad.', type: 'bar', marker: { color: colors.trad.base } },
            { x: xLabels, y: data.withdrawals.roth_basis, name: 'Roth (Basis)', type: 'bar', marker: { color: colors.roth.base } },
            { x: xLabels, y: data.withdrawals.roth_growth, name: 'Roth (Growth)', type: 'bar', marker: { color: colors.roth.light } },
            { x: xLabels, y: data.income.dividends, name: 'Dividends/Interest', type: 'bar', marker: { color: colors.brokerage.dark } },
            { x: xLabels, y: data.withdrawals.brokerage_basis, name: 'Brokerage (Basis)', type: 'bar', marker: { color: colors.brokerage.base } },
            { x: xLabels, y: data.withdrawals.brokerage_growth, name: 'Brokerage (Growth)', type: 'bar', marker: { color: colors.brokerage.light } },
            { x: xLabels, y: data.withdrawals.hsa, name: 'From HSA', type: 'bar', marker: { color: colors.hsa.base } },
            { x: xLabels, y: data.withdrawals.cash, name: 'From Cash', type: 'bar', marker: { color: colors.cash.base } },
            { x: xLabels, y: data.withdrawals.total, name: 'Total Inflow', mode: 'lines', line: { width: 3, color: '#000' } }
        ], {
            ...commonLayout,
            barmode: 'stack',
            yaxis: { ...commonLayout.yaxis, title: 'Amount (Real $)' }
        }, plotConfig);

        // 3. Market Chart
        Plotly.newPlot('market_chart', [
            { x: xLabels, y: data.market.stocks, name: 'Stocks', line: { color: '#2563eb' } },
            { x: xLabels, y: data.market.bonds, name: 'Bonds', line: { color: '#94a3b8' } },
            { x: xLabels, y: data.market.inflation, name: 'Inflation', line: { color: '#f43f5e', dash: 'dot' } }
        ], {
            ...commonLayout,
            yaxis: { title: 'Annual Rate', tickformat: ',.0%' }
        }, plotConfig);

        // 4. Expenses and Savings Chart
        Plotly.newPlot('expenses_chart', [
            { x: xLabels, y: data.outflows.taxes, name: 'Taxes', type: 'bar', marker: { color: colors.outflows.taxes } },
            { x: xLabels, y: data.outflows.mortgage, name: 'Mortgage', type: 'bar', marker: { color: colors.outflows.mortgage } },
            { x: xLabels, y: data.outflows.spending, name: 'Spending', type: 'bar', marker: { color: colors.outflows.spending } },
            { x: xLabels, y: data.outflows.healthcare, name: 'Healthcare', type: 'bar', marker: { color: colors.hsa.dark } },
            { x: xLabels, y: data.savings.to_hsa, name: 'to HSA', type: 'bar', marker: { color: colors.hsa.base } },
            { x: xLabels, y: data.savings.to_trad, name: 'to Trad', type: 'bar', marker: { color: colors.trad.base } },
            { x: xLabels, y: data.savings.to_roth, name: 'to Roth', type: 'bar', marker: { color: colors.roth.base } },
            { x: xLabels, y: data.savings.to_cash, name: 'to Cash', type: 'bar', marker: { color: colors.cash.base } },
            { x: xLabels, y: data.savings.to_brokerage, name: 'to Brokerage', type: 'bar', marker: { color: colors.brokerage.base } },
            { x: xLabels, y: data.outflows.total, name: 'Total Outflow', mode: 'lines', line: { width: 3, color: '#000' } }
        ], {
            ...commonLayout,
            barmode: 'stack',
            yaxis: { ...commonLayout.yaxis, title: 'Amount (Real $)' }
        }, plotConfig);

    } catch (error) {
        console.error("Failed to load dashboard data:", error);
    }
});