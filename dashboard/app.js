/**
 * RecruiterBrain — Dashboard Application
 * Interactive visualization of the 5-layer candidate ranking pipeline.
 */

// ─── Global State ──────────────────────────────────────────────────────────
let dashboardData = null;
let allCandidates = [];
let filteredCandidates = [];

// ─── Initialize ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    initNavigation();
    initFilters();
    initModal();
});

// ─── Data Loading ──────────────────────────────────────────────────────────
async function loadData() {
    try {
        const response = await fetch('data.json');
        dashboardData = await response.json();
        allCandidates = dashboardData.top_candidates || [];
        filteredCandidates = [...allCandidates];

        renderHeroStats();
        renderCandidates();
        renderAnalysis();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        document.getElementById('candidates-grid').innerHTML =
            '<div class="loading">Unable to load data. Make sure data.json is in the dashboard folder.</div>';
    }
}

// ─── Hero Stats ────────────────────────────────────────────────────────────
function renderHeroStats() {
    const meta = dashboardData.metadata;

    animateCounter('stat-total', meta.total_candidates, 0, ',');
    animateCounter('stat-honeypots', meta.honeypots_detected, 0);
    animateCounter('stat-stuffers', meta.stuffers_detected, 0, ',');

    const timeEl = document.getElementById('stat-time');
    timeEl.textContent = `${meta.processing_time_seconds}s`;
}

function animateCounter(elementId, target, decimals = 0, separator = '') {
    const el = document.getElementById(elementId);
    const duration = 1500;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(eased * target);

        if (separator === ',') {
            el.textContent = current.toLocaleString();
        } else {
            el.textContent = decimals > 0 ? current.toFixed(decimals) : current;
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// ─── Navigation ────────────────────────────────────────────────────────────
function initNavigation() {
    const nav = document.getElementById('nav');
    const links = document.querySelectorAll('.nav-link');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }

        // Update active link
        const sections = ['overview', 'pipeline', 'rankings', 'analysis'];
        for (const id of sections.reverse()) {
            const section = document.getElementById(id);
            if (section && section.getBoundingClientRect().top <= 200) {
                links.forEach(l => l.classList.remove('active'));
                const activeLink = document.querySelector(`.nav-link[data-section="${id}"]`);
                if (activeLink) activeLink.classList.add('active');
                break;
            }
        }
    });
}

// ─── Filters ───────────────────────────────────────────────────────────────
function initFilters() {
    // Search
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.toLowerCase().trim();
        filterCandidates(query);
    });

    // Chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            const filter = chip.dataset.filter;
            let maxRank = 100;
            if (filter === 'top10') maxRank = 10;
            else if (filter === 'top25') maxRank = 25;
            else if (filter === 'top50') maxRank = 50;

            filteredCandidates = allCandidates.filter(c => c.rank <= maxRank);
            renderCandidates();
        });
    });
}

function filterCandidates(query) {
    if (!query) {
        filteredCandidates = [...allCandidates];
    } else {
        filteredCandidates = allCandidates.filter(c =>
            c.name.toLowerCase().includes(query) ||
            c.title.toLowerCase().includes(query) ||
            c.company.toLowerCase().includes(query) ||
            c.candidate_id.toLowerCase().includes(query) ||
            c.location.toLowerCase().includes(query) ||
            (c.top_skills && c.top_skills.some(s => s.toLowerCase().includes(query)))
        );
    }
    renderCandidates();
}

// ─── Candidate Cards ───────────────────────────────────────────────────────
function renderCandidates() {
    const grid = document.getElementById('candidates-grid');

    if (filteredCandidates.length === 0) {
        grid.innerHTML = '<div class="loading">No candidates match your search.</div>';
        return;
    }

    grid.innerHTML = filteredCandidates.map((c, i) => {
        const rankClass = c.rank === 1 ? 'gold' : c.rank === 2 ? 'silver' : c.rank === 3 ? 'bronze' : 'default';
        const skills = (c.top_skills || []).slice(0, 5);

        return `
            <div class="candidate-card" data-index="${allCandidates.indexOf(c)}" style="animation-delay: ${i * 0.03}s">
                <div class="card-header">
                    <div>
                        <span class="card-rank ${rankClass}">#${c.rank}</span>
                    </div>
                    <div class="card-score">${c.score.toFixed(4)}</div>
                </div>
                <div class="card-name">${c.name}</div>
                <div class="card-title">${c.title}</div>
                <div class="card-company">${c.company} · ${c.location}</div>
                <div class="card-meta">
                    <span class="card-meta-item">${c.yoe.toFixed(1)} yrs exp</span>
                    <span class="card-meta-item">${(c.response_rate * 100).toFixed(0)}% response</span>
                    <span class="card-meta-item">${c.notice_period}d notice</span>
                </div>
                <div class="card-scores">
                    <div class="mini-score">
                        <div class="mini-score-value">${(c.career_fit * 100).toFixed(0)}%</div>
                        <div class="mini-score-label">Career</div>
                    </div>
                    <div class="mini-score">
                        <div class="mini-score-value">${(c.skills_match * 100).toFixed(0)}%</div>
                        <div class="mini-score-label">Skills</div>
                    </div>
                    <div class="mini-score">
                        <div class="mini-score-value">${(c.behavioral * 100).toFixed(0)}%</div>
                        <div class="mini-score-label">Behavioral</div>
                    </div>
                    <div class="mini-score">
                        <div class="mini-score-value">${(c.education * 100).toFixed(0)}%</div>
                        <div class="mini-score-label">Education</div>
                    </div>
                </div>
                ${skills.length > 0 ? `
                    <div class="card-skills">
                        ${skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');

    // Add click handlers
    grid.querySelectorAll('.candidate-card').forEach(card => {
        card.addEventListener('click', () => {
            const index = parseInt(card.dataset.index);
            openModal(allCandidates[index]);
        });
    });
}

// ─── Modal ─────────────────────────────────────────────────────────────────
function initModal() {
    const overlay = document.getElementById('modal-overlay');
    const closeBtn = document.getElementById('modal-close');

    closeBtn.addEventListener('click', () => overlay.classList.remove('active'));
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('active');
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') overlay.classList.remove('active');
    });
}

function openModal(candidate) {
    const overlay = document.getElementById('modal-overlay');
    const content = document.getElementById('modal-content');

    const c = candidate;
    const skills = (c.top_skills || []);

    const scoreItems = [
        { label: 'Career Fit', value: c.career_fit, color: '#6366f1' },
        { label: 'Title Match', value: c.title_score || 0, color: '#818cf8' },
        { label: 'Experience', value: c.exp_score || 0, color: '#a78bfa' },
        { label: 'Industry', value: c.industry_score || 0, color: '#c084fc' },
        { label: 'Production ML', value: c.prod_ml_score || 0, color: '#6366f1' },
        { label: 'Skills Match', value: c.skills_match, color: '#06b6d4' },
        { label: 'Must-Have Skills', value: c.must_have_score || 0, color: '#22d3ee' },
        { label: 'Nice-to-Have', value: c.nice_to_have_score || 0, color: '#67e8f9' },
        { label: 'Behavioral', value: c.behavioral, color: '#10b981' },
        { label: 'Engagement', value: c.engagement_score || 0, color: '#34d399' },
        { label: 'Availability', value: c.availability_score || 0, color: '#6ee7b7' },
        { label: 'Education', value: c.education, color: '#f59e0b' },
    ];

    const responseClass = c.response_rate >= 0.5 ? 'positive' : c.response_rate >= 0.2 ? 'warning' : 'negative';
    const githubClass = c.github_score >= 40 ? 'positive' : c.github_score >= 15 ? 'warning' : c.github_score < 0 ? 'neutral' : 'negative';
    const noticeClass = c.notice_period <= 30 ? 'positive' : c.notice_period <= 60 ? 'warning' : 'negative';

    content.innerHTML = `
        <div class="modal-header">
            <div class="modal-rank-badge">Rank #${c.rank} · Score ${c.score.toFixed(4)}</div>
            <div class="modal-name">${c.name}</div>
            <div class="modal-title-company">${c.title} at ${c.company} · ${c.location}, ${c.country}</div>
        </div>

        <div class="modal-scores-grid">
            ${scoreItems.map(s => `
                <div class="modal-score-item">
                    <div class="modal-score-header">
                        <span class="modal-score-label">${s.label}</span>
                        <span class="modal-score-value">${(s.value * 100).toFixed(1)}%</span>
                    </div>
                    <div class="modal-score-bar">
                        <div class="modal-score-fill" style="width: ${s.value * 100}%; background: ${s.color}"></div>
                    </div>
                </div>
            `).join('')}
        </div>

        <div class="modal-section">
            <h4>Behavioral Signals</h4>
            <div class="modal-signals">
                <div class="signal-item">
                    <div class="signal-value ${responseClass}">${(c.response_rate * 100).toFixed(0)}%</div>
                    <div class="signal-label">Response Rate</div>
                </div>
                <div class="signal-item">
                    <div class="signal-value ${githubClass}">${c.github_score >= 0 ? c.github_score.toFixed(0) : 'N/A'}</div>
                    <div class="signal-label">GitHub Score</div>
                </div>
                <div class="signal-item">
                    <div class="signal-value ${noticeClass}">${c.notice_period}d</div>
                    <div class="signal-label">Notice Period</div>
                </div>
                <div class="signal-item">
                    <div class="signal-value ${c.open_to_work ? 'positive' : 'warning'}">${c.open_to_work ? 'Yes' : 'No'}</div>
                    <div class="signal-label">Open to Work</div>
                </div>
                <div class="signal-item">
                    <div class="signal-value neutral">${c.work_mode}</div>
                    <div class="signal-label">Work Mode</div>
                </div>
                <div class="signal-item">
                    <div class="signal-value neutral">${c.yoe.toFixed(1)}yr</div>
                    <div class="signal-label">Experience</div>
                </div>
            </div>
        </div>

        ${skills.length > 0 ? `
            <div class="modal-section">
                <h4>Key Skills (Expert/Advanced)</h4>
                <div class="card-skills">
                    ${skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}
                </div>
            </div>
        ` : ''}
    `;

    overlay.classList.add('active');

    // Animate score bars
    setTimeout(() => {
        content.querySelectorAll('.modal-score-fill').forEach(bar => {
            const width = bar.style.width;
            bar.style.width = '0%';
            setTimeout(() => { bar.style.width = width; }, 50);
        });
    }, 100);
}

// ─── Analysis Charts ───────────────────────────────────────────────────────
function renderAnalysis() {
    renderScoreBreakdown();
    renderDimensionChart();
    renderTitleDistribution();
}

function renderScoreBreakdown() {
    const container = document.getElementById('score-breakdown-chart');
    const top10 = allCandidates.slice(0, 10);

    let html = '';
    top10.forEach(c => {
        const total = c.career_fit * 0.4 + c.skills_match * 0.3 + c.behavioral * 0.2 + c.education * 0.1;
        const careerW = (c.career_fit * 0.4 / Math.max(total, 0.01)) * 100;
        const skillsW = (c.skills_match * 0.3 / Math.max(total, 0.01)) * 100;
        const behavW = (c.behavioral * 0.2 / Math.max(total, 0.01)) * 100;
        const eduW = (c.education * 0.1 / Math.max(total, 0.01)) * 100;

        html += `
            <div class="breakdown-row">
                <span class="breakdown-rank">#${c.rank}</span>
                <span class="breakdown-name" title="${c.name}">${c.name.split(' ')[0]}</span>
                <div class="breakdown-bars">
                    <div class="breakdown-segment career" style="width: ${careerW}%" title="Career: ${(c.career_fit * 100).toFixed(0)}%"></div>
                    <div class="breakdown-segment skills" style="width: ${skillsW}%" title="Skills: ${(c.skills_match * 100).toFixed(0)}%"></div>
                    <div class="breakdown-segment behavioral" style="width: ${behavW}%" title="Behavioral: ${(c.behavioral * 100).toFixed(0)}%"></div>
                    <div class="breakdown-segment education" style="width: ${eduW}%" title="Education: ${(c.education * 100).toFixed(0)}%"></div>
                </div>
                <span class="breakdown-total">${c.score.toFixed(3)}</span>
            </div>
        `;
    });

    html += `
        <div class="chart-legend">
            <div class="legend-item"><span class="legend-dot career"></span>Career Fit (40%)</div>
            <div class="legend-item"><span class="legend-dot skills"></span>Skills (30%)</div>
            <div class="legend-item"><span class="legend-dot behavioral"></span>Behavioral (20%)</div>
            <div class="legend-item"><span class="legend-dot education"></span>Education (10%)</div>
        </div>
    `;

    container.innerHTML = html;
}

function renderDimensionChart() {
    const container = document.getElementById('dimension-chart');
    const dims = ['career_fit', 'skills_match', 'behavioral', 'education'];
    const labels = ['Career Fit', 'Skills Match', 'Behavioral', 'Education'];
    const classes = ['career', 'skills', 'behavioral', 'education'];

    let html = '<div class="bar-chart">';

    dims.forEach((dim, i) => {
        const values = allCandidates.map(c => c[dim]);
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const max = Math.max(...values);
        const min = Math.min(...values);

        html += `
            <div class="bar-row">
                <span class="bar-label">${labels[i]} (avg)</span>
                <div class="bar-track">
                    <div class="bar-fill ${classes[i]}" style="width: ${avg * 100}%">${(avg * 100).toFixed(1)}%</div>
                </div>
            </div>
            <div class="bar-row">
                <span class="bar-label">${labels[i]} (max)</span>
                <div class="bar-track">
                    <div class="bar-fill ${classes[i]}" style="width: ${max * 100}%; opacity: 0.7">${(max * 100).toFixed(1)}%</div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

function renderTitleDistribution() {
    const container = document.getElementById('title-chart');
    const titleCounts = {};

    allCandidates.forEach(c => {
        const title = c.title || 'Unknown';
        titleCounts[title] = (titleCounts[title] || 0) + 1;
    });

    const sorted = Object.entries(titleCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 12);

    const maxCount = sorted[0]?.[1] || 1;
    const colors = ['#6366f1', '#818cf8', '#a78bfa', '#c084fc',
                    '#06b6d4', '#22d3ee', '#10b981', '#34d399',
                    '#f59e0b', '#fbbf24', '#f43f5e', '#fb7185'];

    let html = '<div class="bar-chart">';
    sorted.forEach(([title, count], i) => {
        const pct = (count / maxCount) * 100;
        html += `
            <div class="bar-row">
                <span class="bar-label" title="${title}">${title}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width: ${pct}%; background: ${colors[i % colors.length]}">${count}</div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}
