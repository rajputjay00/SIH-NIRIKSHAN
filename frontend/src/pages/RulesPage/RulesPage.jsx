import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useT } from '../../i18n/useT';
import styles from './RulesPage.module.css';

const PENDING_RULES = [
  {
    id: 'R18',
    rule_ref: 'Rule 18',
    title_en: 'Scale Calibration & Tolerances',
    title_hi: 'तराजू अंशांकन एवं सहिष्णुता',
    severity: 'medium',
    status: 'pending',
    reason: 'scale calibration',
    category: 'weight',
    message_en: 'Physical scale calibration and maximum permissible error verification under First Schedule.',
    message_hi: 'प्रथम अनुसूची के तहत भौतिक तराजू अंशांकन और अधिकतम अनुमेय त्रुटि सत्यापन।',
    fix_hint_en: 'Calibrate weighing instrument and verify scale calibration certificate.',
    fix_hint_hi: 'तौल उपकरण को अंशांकित करें और पैमाने का अंशांकन प्रमाण पत्र सत्यापित करें।',
    source: 'LMPC Rules 2011, Rule 18',
  },
];

export function RulesPage() {
  const { lang, setLang } = useT();
  const [searchParams] = useSearchParams();
  const urlQuery = searchParams.get('q') || '';

  const [allRules, setAllRules] = useState([]);
  const [rulesVersion, setRulesVersion] = useState('0.4.0');
  const [counts, setCounts] = useState({ lmpc: 34, cross: 5, pend: 1 });
  const [search, setSearch] = useState(urlQuery);
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [flippedCards, setFlippedCards] = useState({});

  useEffect(() => {
    setSearch(urlQuery);
  }, [urlQuery]);

  useEffect(() => {
    const fetchActiveRules = async () => {
      try {
        const res = await fetch('/api/rules');
        if (res.ok) {
          const data = await res.json();
          setRulesVersion(data.rules_version || data.version || '0.4.0');
          const rulesList = Array.isArray(data.rules)
            ? data.rules
            : (Array.isArray(data) ? data : Object.values(data.rules || data || {}));

          const parsed = rulesList.map((r) => ({
            id: r.id,
            rule_ref: r.rule_ref || r.id,
            title_en: r.title_en || r.description || r.id,
            title_hi: r.title_hi || r.title_en || r.id,
            severity: r.severity || 'high',
            status: 'active',
            category: r.category || 'labelling',
            message_en: r.message_en || r.requirement || r.title_en || '',
            message_hi: r.message_hi || r.requirement_hi || r.message_en || r.title_hi || '',
            fix_hint_en: r.fix_hint_en || r.fix_hint || '',
            fix_hint_hi: r.fix_hint_hi || r.fix_hint || '',
            source: r.source || 'LMPC Rules 2011',
          }));

          const lmpc = parsed.filter((r) => r.id && /^R/.test(r.id)).length;
          const cross = parsed.filter((r) => r.id && /^C/.test(r.id)).length;
          const pend = PENDING_RULES.length;

          setCounts({ lmpc, cross, pend });
          setAllRules([...parsed, ...PENDING_RULES]);
        }
      } catch (err) {
        // quiet fallback
      }
    };

    fetchActiveRules();
  }, []);

  const toggleFlip = (id) => {
    setFlippedCards((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredRules = allRules.filter((r) => {
    const matchesSearch =
      r.id.toLowerCase().includes(search.toLowerCase()) ||
      r.rule_ref.toLowerCase().includes(search.toLowerCase()) ||
      (r.title_en && r.title_en.toLowerCase().includes(search.toLowerCase())) ||
      (r.title_hi && r.title_hi.toLowerCase().includes(search.toLowerCase())) ||
      (r.message_en && r.message_en.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
    const matchesSeverity = severityFilter === 'all' || r.severity === severityFilter;

    return matchesSearch && matchesStatus && matchesSeverity;
  });

  return (
    <div className={styles.rulesContainer}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Rules-as-Code Explorer</h1>
          <p className={styles.subtitle}>
            {counts.lmpc} LMPC rules implemented · {counts.cross} cross-surface checks · {counts.pend} pending (R18, scale calibration) • <strong style={{ color: 'var(--blue-500)' }}>v{rulesVersion}</strong>
          </p>
        </div>

        <button
          className={styles.selectInput}
          onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
        >
          🌐 Language: {lang === 'en' ? 'English' : 'हिन्दी'}
        </button>
      </div>

      {/* Filter Bar */}
      <div className={styles.filterBar}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search rule ID, reference, title or requirement..."
          className={styles.searchInput}
        />

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={styles.selectInput}
        >
          <option value="all">All Statuses</option>
          <option value="active">Active Engine Rules ({counts.lmpc + counts.cross})</option>
          <option value="pending">Pending Rules ({counts.pend})</option>
        </select>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className={styles.selectInput}
        >
          <option value="all">All Severities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Cards Grid */}
      <div className={styles.cardsGrid}>
        {filteredRules.map((rule) => {
          const isFlipped = Boolean(flippedCards[rule.id]);
          const title = lang === 'hi' && rule.title_hi ? rule.title_hi : rule.title_en;
          const requirement = lang === 'hi' && rule.message_hi ? rule.message_hi : rule.message_en;
          const fixHint = lang === 'hi' && rule.fix_hint_hi ? rule.fix_hint_hi : rule.fix_hint_en;

          return (
            <div
              key={rule.id}
              className={`${styles.flipCard} ${isFlipped ? styles.flipped : ''}`}
              onClick={() => toggleFlip(rule.id)}
            >
              <div className={styles.flipCardInner}>
                {/* Front Side */}
                <div className={styles.cardFront}>
                  <div className={styles.cardFrontMain}>
                    <div className={styles.ruleHeader}>
                      <span className={styles.ruleRef}>{rule.rule_ref}</span>
                      <span
                        className={`${styles.statusChip} ${
                          rule.status === 'active' ? styles.statusActive : styles.statusPlanned
                        }`}
                      >
                        {rule.status}
                      </span>
                    </div>

                    <h3 className={styles.ruleTitle}>{title}</h3>

                    <p className={styles.requirementText}>{requirement}</p>
                  </div>

                  <div className={styles.cardFrontFooter}>
                    <div className={styles.severityRow}>
                      <span className={styles.severityTag}>
                        Severity: <strong className={styles[rule.severity || 'high']}>{(rule.severity || 'high').toUpperCase()}</strong>
                      </span>
                      <span className={styles.sourceTag}>{rule.source}</span>
                    </div>
                    <div className={styles.flipHint}>Click to flip detail ↻</div>
                  </div>
                </div>

                {/* Back Side */}
                <div className={styles.cardBack}>
                  <div className={styles.detailSection}>
                    <div>
                      <span className={styles.detailLabel}>Requirement: </span>
                      {requirement}
                    </div>
                    {fixHint && (
                      <div>
                        <span className={styles.detailLabel}>Fix Hint: </span>
                        {fixHint}
                      </div>
                    )}
                    <div>
                      <span className={styles.detailLabel}>Rule ID: </span>
                      <code>{rule.id}</code> ({rule.rule_ref})
                    </div>
                  </div>

                  <div className={styles.cardBackFooter}>
                    <span className={styles.sourceTag}>{rule.source}</span>
                    <span className={styles.flipHint}>Click to flip back ↺</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
