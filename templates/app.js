const { useState, useEffect, useCallback, createElement } = React;
const { createRoot } = ReactDOM;

// -- ヘルパー関数 --
const formatDateTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
};

// -- UIコンポーネント (既存、変更なし) --
const PnChart = ({ chartData, title }) => {
    const canvasRef = React.useRef(null);

    useEffect(() => {
        if (!chartData || chartData === "") {
            return;
        }

        const ctx = canvasRef.current.getContext('2d');
        let chartInstance = Chart.getChart(ctx);
        if (chartInstance) {
            chartInstance.destroy();
        }

        const chartImage = new Image();
        chartImage.onload = () => {
            canvasRef.current.width = chartImage.width;
            canvasRef.current.height = chartImage.height;
            ctx.drawImage(chartImage, 0, 0);
        };
        chartImage.src = `data:image/png;base64,${chartData}`;

    }, [chartData]);

    if (!chartData || chartData === "") {
        return <div className="alert alert-info">データがありません。</div>;
    }

    return (
        <div className="chart-container">
            <h5>{title}</h5>
            <canvas ref={canvasRef}></canvas>
        </div>
    );
};

const ImportanceRanking = ({ clusters, onClusterClick }) => {
    if (!clusters || clusters.length === 0) {
        return <div className="alert alert-info">重要度ランキングデータがありません。</div>;
    }

    return (
        <div className="card ranking-container">
            <div className="card-header">
                重要度コメントランキング
            </div>
            <ul className="list-group list-group-flush">
                {clusters.map((cluster, index) => (
                    <li key={cluster.cluster_id} className="list-group-item">
                        <div className="d-flex w-100 justify-content-between align-items-center">
                            <h6 className="mb-1">
                                {index + 1}. スコア: {cluster.score} (コメント数: {cluster.comment_count})
                            </h6>
                            <button className="btn btn-sm btn-primary" onClick={() => onClusterClick(cluster.cluster_id)}>
                                コメントを見る
                            </button>
                        </div>
                        <p className="mb-1">代表コメント: {cluster.representative_text}</p>
                        <div>
                            {/* ★★★ ここを修正 ★★★ */}
                            {cluster.tags && Object.entries(cluster.tags).map(([key, value]) => (
                                // value が 1 または 緊急性で値が 0 より大きい場合に表示
                                (value === 1 || (key === '緊急性' && value > 0)) && (
                                    <span key={key} className="badge bg-secondary tag-badge">
                                        {key === '緊急性' ? `${key}:${value}` : key}
                                    </span>
                                )
                            ))}
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
};

const CommentDetailsModal = ({ show, onClose, clusterDetails }) => {
    if (!show || !clusterDetails) return null;

    return (
        <div className={`modal fade ${show ? 'show d-block' : ''}`} tabIndex="-1" role="dialog" style={{backgroundColor: 'rgba(0,0,0,0.5)'}}>
            <div className="modal-dialog modal-lg" role="document">
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">クラスタID: {clusterDetails.cluster_id} のコメント詳細</h5>
                        <button type="button" className="btn-close" onClick={onClose}></button>
                    </div>
                    <div className="modal-body">
                        <h6>代表コメント:</h6>
                        <p>{clusterDetails.representative_text}</p>
                        <h6>構成コメント ({clusterDetails.comments.length}件):</h6>
                        <ul className="list-unstyled">
                            {clusterDetails.comments.map(comment => (
                                <li key={comment.id} className="border p-2 mb-2 rounded">
                                    <small className="text-muted">スコア: {comment.importance_score !== null ? comment.importance_score.toFixed(2) : 'N/A'}</small><br/>
                                    {comment.text} <br/>
                                    <small className="text-muted">
                                        カテゴリ: {comment.category || 'N/A'}, 感情: {comment.sentiment === 1 ? 'Positive' : comment.sentiment === 0 ? 'Negative' : 'N/A'}, 危険性: {comment.danger ? 'Yes' : 'No'}
                                    </small><br/>
                                    {comment.tags && Object.entries(comment.tags).map(([key, value]) => (
                                        (value === 1 || (key === '緊急性' && value > 0)) && <span key={key} className="badge bg-info text-dark me-1 tag-badge">{key}: {value}</span>
                                    ))}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="modal-footer">
                        <button type="button" className="btn btn-secondary" onClick={onClose}>閉じる</button>
                    </div>
                </div>
            </div>
        </div>
    );
};


// -- 新規コンポーネント: ホームページ (時系列グラフ) --
const HomePage = ({ loadingAnalysis, timeSeriesData }) => { // loadingUpload, uploadMessage, handleFileUpload プロップを削除
    const overallChartRef = React.useRef(null);
    const categoryChartsRef = React.useRef({}); // カテゴリ別チャートの参照

    // チャートインスタンスを保存するMap
    const chartInstances = React.useRef(new Map());

    useEffect(() => {
        // 既存のチャートをすべて破棄
        chartInstances.current.forEach(chart => chart.destroy());
        chartInstances.current.clear();

        if (loadingAnalysis || !timeSeriesData || !timeSeriesData.dates || timeSeriesData.dates.length === 0) {
            return;
        }

        // 全体ポジティブ比率の推移グラフ
        const overallCtx = overallChartRef.current.getContext('2d');
        const overallChart = new Chart(overallCtx, {
            type: 'line',
            data: {
                labels: timeSeriesData.dates.map(d => formatDateTime(d).split(' ')[0]),
                datasets: [
                    {
                        label: '全体ポジティブ (%)',
                        data: timeSeriesData.overall_positive_percents,
                        borderColor: 'skyblue',
                        backgroundColor: 'rgba(135, 206, 235, 0.2)',
                        fill: false,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: { title: { display: true, text: '全体ポジティブコメント比率の推移' } },
                scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: 'ポジティブ (%)' } } }
            }
        });
        chartInstances.current.set('overall', overallChart);


        // カテゴリ別ポジティブ比率の推移グラフ
        Object.keys(timeSeriesData.category_positive_percents).forEach(category => {
            const catCanvas = categoryChartsRef.current[category];
            if (!catCanvas) return;

            const catCtx = catCanvas.getContext('2d');
            if (catCanvas.chart) {
                catCanvas.chart.destroy();
            }

            const categoryDataPoints = timeSeriesData.category_positive_percents[category];
            const categoryDates = categoryDataPoints.map(d => formatDateTime(d.date).split(' ')[0]);
            const categoryPercents = categoryDataPoints.map(d => d.percent);

            catCanvas.chart = new Chart(catCtx, {
                type: 'line',
                data: {
                    labels: categoryDates,
                    datasets: [
                        {
                            label: `${category} ポジティブ (%)`,
                            data: categoryPercents,
                            borderColor: 'lightgreen',
                            backgroundColor: 'rgba(144, 238, 144, 0.2)',
                            fill: false,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: { title: { display: true, text: `${category} ポジティブコメント比率の推移` } },
                    scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: 'ポジティブ (%)' } } }
                }
            });
            chartInstances.current.set(category, catCanvas.chart);
        });

        return () => {
            chartInstances.current.forEach(chart => chart.destroy());
            chartInstances.current.clear();
        };

    }, [loadingAnalysis, timeSeriesData]);


    return (
        <div>
            {/* CSVアップロードフォームはAppコンポーネントのサイドバーに移動したので削除 */}
            {/* <section>
                <h2 className="section-header">1. CSVアップロード</h2>
                <form onSubmit={handleFileUpload} className="mb-4">
                    <div className="input-group">
                        <input type="file" name="file" className="form-control" accept=".csv" required disabled={loading} />
                        <button type="submit" className="btn btn-primary" disabled={loading}>
                            {loading ? (
                                <>
                                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                    処理中...
                                </>
                            ) : (
                                "アップロード & 分析"
                            )}
                        </button>
                    </div>
                    {loading && <div className="text-center mt-3"><div className="spinner-border text-primary" role="status"><span className="visually-hidden">Loading...</span></div> 処理中...</div>}
                    {uploadMessage.message && (
                        <div className={`alert mt-3 ${uploadMessage.status === 'success' ? 'alert-success' : uploadMessage.status === 'error' ? 'alert-danger' : 'alert-info'}`}>
                            {uploadMessage.message}
                        </div>
                    )}
                </form>
            </section> */}

            <section>
                <h2 className="section-header">授業評価の変遷 (ホーム)</h2>
                {loadingAnalysis ? (
                    <div className="text-center py-5">
                        <div className="spinner-border text-primary" style={{width: '3rem', height: '3rem'}} role="status">
                            <span className="visually-hidden">読み込み中...</span>
                        </div>
                        <p className="mt-3">時系列データを読み込み中...</p>
                    </div>
                ) : (
                    <div className="row">
                        <div className="col-12 chart-container">
                            <h5>全体ポジティブコメント比率の推移</h5>
                            <canvas ref={overallChartRef}></canvas>
                        </div>
                        {timeSeriesData?.category_positive_percents && Object.keys(timeSeriesData.category_positive_percents).length > 0 ? (
                            Object.keys(timeSeriesData.category_positive_percents).map(category => (
                                <div key={category} className="col-md-6 chart-container">
                                    <h5>カテゴリ: {category} ポジティブコメント比率の推移</h5>
                                    <canvas ref={el => categoryChartsRef.current[category] = el}></canvas>
                                </div>
                            ))
                        ) : (
                            <div className="col-12 alert alert-info chart-container">カテゴリ別時系列データがありません。</div>
                        )}
                        {(!timeSeriesData || timeSeriesData.dates.length === 0) && (
                            <div className="alert alert-info">時系列データがありません。コメントをアップロードして分析してください。</div>
                        )}
                    </div>
                )}
            </section>
        </div>
    );
};

// -- 分析結果表示ページ (AnalysisPage) --
const AnalysisPage = ({ loadingAnalysis, pnCharts, topClusters, aiAnalysisComment, onClusterClick, activeContent, setActiveContent, currentSessionId }) => {
    // 表示するコンテンツの切り替えボタン
    // Sidebarではなく、このページ内にタブとして配置
    const getAnalysisPageTitle = () => {
        if (currentSessionId) {
            return `分析結果 (履歴セッションID: ${currentSessionId})`;
        }
        return `最新分析結果`;
    };

    return (
        <div>
            <h2 className="section-header">{getAnalysisPageTitle()}</h2>
            
            <div className="mb-4">
                <div className="nav nav-tabs" id="analysisTabs" role="tablist">
                    <button className={`nav-link ${activeContent === 'pn_charts' ? 'active' : ''}`} 
                            onClick={() => setActiveContent('pn_charts')}
                            type="button" role="tab">
                        PN比グラフ
                    </button>
                    <button className={`nav-link ${activeContent === 'ranking' ? 'active' : ''}`} 
                            onClick={() => setActiveContent('ranking')}
                            type="button" role="tab">
                        重要度コメントランキング
                    </button>
                    <button className={`nav-link ${activeContent === 'ai_comment' ? 'active' : ''}`} 
                            onClick={() => setActiveContent('ai_comment')}
                            type="button" role="tab">
                        AI分析コメント
                    </button>
                </div>
            </div>

            {loadingAnalysis ? (
                <div className="text-center py-5">
                    <div className="spinner-border text-primary" style={{width: '3rem', height: '3rem'}} role="status">
                        <span className="visually-hidden">読み込み中...</span>
                    </div>
                    <p className="mt-3">分析結果を読み込み中...</p>
                </div>
            ) : (
                <div className="tab-content">
                    {/* PN比グラフの表示 */}
                    {activeContent === 'pn_charts' && (
                        <div className="tab-pane fade show active" role="tabpanel">
                            <div className="row">
                                <div className="col-md-6">
                                    <PnChart chartData={pnCharts?.total_pn_chart} title="全体コメント PN比" />
                                </div>
                                <div className="col-md-6">
                                    {pnCharts?.category_pn_charts && Object.keys(pnCharts.category_pn_charts).length > 0 ? (
                                        Object.entries(pnCharts.category_pn_charts).map(([category, chartData]) => (
                                            <PnChart key={category} chartData={chartData} title={`カテゴリ: ${category} PN比`} />
                                        ))
                                    ) : (
                                        <div className="alert alert-info chart-container">カテゴリ別PN比データがありません。</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 重要度コメントランキングの表示 */}
                    {activeContent === 'ranking' && (
                        <div className="tab-pane fade show active" role="tabpanel">
                            <ImportanceRanking clusters={topClusters} onClusterClick={onClusterClick} />
                        </div>
                    )}

                    {/* AI分析コメントの表示 */}
                    {activeContent === 'ai_comment' && (
                        <div className="tab-pane fade show active" role="tabpanel">
                            <div className="card analysis-comment-container">
                                <div className="card-header">
                                    AI分析コメント
                                </div>
                                <div className="card-body">
                                    {aiAnalysisComment ? (
                                        <p style={{ whiteSpace: 'pre-wrap' }}>{aiAnalysisComment}</p>
                                    ) : (
                                        <div className="alert alert-info">AI分析コメントがありません。</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

// -- 新規コンポーネント: 履歴ページ (HistoryPage) --
const HistoryPage = ({ loadingHistory, analysisSessions, onSessionClick }) => {
    if (loadingHistory) {
        return (
            <div className="text-center py-5">
                <div className="spinner-border" role="status" style={{width: '3rem', height: '3rem'}}>
                    <span className="visually-hidden">履歴を読み込み中...</span>
                </div>
                <p className="mt-3">分析履歴を読み込み中...</p>
            </div>
        );
    }

    if (!analysisSessions || analysisSessions.length === 0) {
        return <div className="alert alert-info">分析履歴がありません。CSVをアップロードして分析してください。</div>;
    }

    return (
        <div className="history-list-container">
            <h2 className="section-header">分析履歴</h2>
            <ul className="list-group">
                {analysisSessions.map(session => (
                    <li key={session.id} className="list-group-item d-flex justify-content-between align-items-center history-list-item" onClick={() => onSessionClick(session.id)}>
                        <div>
                            <h5>{formatDateTime(session.created_at)} - {session.csv_filename}</h5>
                            <small className="text-muted">
                                コメント総数: {session.total_comments}件 / 
                                P: {session.overall_positive_percent}% / 
                                N: {session.overall_negative_percent}% / 
                                危険コメント: {session.dangerous_comment_count}件
                            </small>
                        </div>
                        <span className="badge bg-primary rounded-pill">詳細を見る</span>
                    </li>
                ))}
            </ul>
        </div>
    );
};


// -- メインアプリケーションコンポーネント (App) --
const App = () => {
    // 全体的なローディング状態
    const [loadingAnalysis, setLoadingAnalysis] = useState(true); // ホーム/分析ページのコンテンツ読み込み中
    const [loadingUpload, setLoadingUpload] = useState(false); // ファイルアップロードとバックエンド処理中
    const [loadingHistory, setLoadingHistory] = useState(true); // 履歴リスト読み込み中

    // 分析結果データ
    const [pnCharts, setPnCharts] = useState(null);
    const [topClusters, setTopClusters] = useState([]);
    const [aiAnalysisComment, setAiAnalysisComment] = useState("");
    const [analysisSessions, setAnalysisSessions] = useState([]); // 分析履歴リスト用ステート
    const [timeSeriesData, setTimeSeriesData] = useState(null); // 時系列データ用ステート

    // モーダル関連
    const [selectedClusterDetails, setSelectedClusterDetails] = useState(null);
    const [showModal, setShowModal] = useState(false);
    
    // UIメッセージ
    const [uploadMessage, setUploadMessage] = useState({status: '', message: ''});

    // ルーティング関連: 現在のパスと、表示するセッションID
    const [path, setPath] = useState(window.location.pathname);
    const [currentSessionId, setCurrentSessionId] = useState(null); // 現在表示中の履歴セッションID

    // 表示中のコンテンツを管理するステート (AnalysisPage内でのみ有効)
    const [activeContent, setActiveContent] = useState('pn_charts'); 

    // -- API呼び出し関数 --
    // 分析結果（PNグラフ、ランキング、AIコメント）をフェッチ
    const fetchAnalysisResults = useCallback(async (sessionId = null) => {
        try {
            setLoadingAnalysis(true);
            const url = sessionId ? `/api/analysis_results?session_id=${sessionId}` : '/api/analysis_results';
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '分析結果の取得に失敗しました。');
            }
            const data = await response.json();
            setPnCharts(data.pn_charts);
            setTopClusters(data.top_clusters);
            
            const aiUrl = sessionId ? `/api/ai_analysis_comment?session_id=${sessionId}` : '/api/ai_analysis_comment';
            const aiResponse = await fetch(aiUrl);
            if (!aiResponse.ok) {
                const aiErrorData = await aiResponse.json();
                throw new Error(aiErrorData.detail || 'AI分析コメントの取得に失敗しました。');
            }
            const aiData = await aiResponse.json();
            setAiAnalysisComment(aiData.comment);

        } catch (error) {
            console.error('Error fetching analysis results or AI comment:', error);
            setUploadMessage({status: 'error', message: error.message || '分析結果の取得中にエラーが発生しました。'});
            setPnCharts(null); // データ取得失敗時はクリア
            setTopClusters([]);
            setAiAnalysisComment("");
        } finally {
            setLoadingAnalysis(false);
        }
    }, []);

    // 分析履歴リストをフェッチ
    const fetchAnalysisSessions = useCallback(async () => {
        try {
            setLoadingHistory(true);
            const response = await fetch('/api/analysis_sessions');
            if (!response.ok) {
                throw new Error('分析履歴の取得に失敗しました。');
            }
            const data = await response.json();
            setAnalysisSessions(data);
        } catch (error) {
            console.error('Error fetching analysis sessions:', error);
            setUploadMessage({status: 'error', message: error.message || '分析履歴の取得中にエラーが発生しました。'});
            setAnalysisSessions([]);
        } finally {
            setLoadingHistory(false);
        }
    }, []);

    // 時系列データをフェッチ (ホームページ用)
    const fetchTimeSeriesData = useCallback(async () => {
        try {
            setLoadingAnalysis(true); // ホームページのローディングも AnalysisPage と共有
            const response = await fetch('/api/time_series_data');
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '時系列データの取得に失敗しました。');
            }
            const data = await response.json();
            setTimeSeriesData(data);
        } catch (error) {
            console.error('Error fetching time series data:', error);
            setUploadMessage({status: 'error', message: error.message || '時系列データの取得中にエラーが発生しました。'});
            setTimeSeriesData(null);
        } finally {
            setLoadingAnalysis(false);
        }
    }, []);

    // CSVアップロード処理
    const handleFileUpload = async (event) => {
        event.preventDefault();
        const formData = new FormData(event.target);
        
        setUploadMessage({status: 'info', message: 'ファイルのアップロードと分析処理を開始しました...'});
        setLoadingUpload(true);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            if (response.redirected) {
                setUploadMessage({status: 'success', message: 'ファイルのアップロードと分析処理が完了しました。結果を読み込み中...'});
                // リダイレクト後はURLが '/' になるので、その後のデータフェッチをトリガー
                // ホームページと履歴ページの両方のデータを更新する
                await fetchTimeSeriesData(); // ホームページ用に時系列データ再フェッチ
                await fetchAnalysisSessions(); // 履歴ページ用に履歴リスト再フェッチ
                setPath('/'); // URLパスをホームに戻す
                setCurrentSessionId(null); // 最新のセッションを表示
            } else if (response.ok) { // fallback (現在の /upload はリダイレクトなのでここには来ないはず)
                const data = await response.json();
                setUploadMessage({status: 'success', message: data.message});
                await fetchTimeSeriesData();
                await fetchAnalysisSessions();
                setPath('/');
                setCurrentSessionId(null);
            } else {
                const errorData = await response.json();
                setUploadMessage({status: 'error', message: errorData.detail || 'ファイルのアップロードに失敗しました。'});
            }
        } catch (error) {
            console.error('Upload Error:', error);
            setUploadMessage({status: 'error', message: 'ネットワークエラー、または予期せぬエラーが発生しました。エラーの詳細についてはコンソールを確認してください。'});
        } finally {
            setLoadingUpload(false);
        }
    };

    // クラスタ詳細の取得とモーダル表示
    const handleClusterClick = async (clusterId) => {
        try {
            // ★★★ ここを修正します ★★★
            // テンプレートリテラルの記述が間違っている可能性
            // 正しくはバッククォート (`) で囲み、変数を ${変数名} で埋め込みます
            const url = currentSessionId 
                ? `/api/cluster_details/${clusterId}?session_id=${currentSessionId}` 
                : `/api/cluster_details/${clusterId}`;
            // 以前のコードでは、おそらく `url` の変数定義がバッククォートではなくクォートで囲まれていたため、
            // 変数の中身が文字列としてそのまま送られていました。
            // 正しいテンプレートリテラルの例: `これは${変数}です`

            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'クラスタ詳細の取得に失敗しました。');
            }
            const data = await response.json();
            setSelectedClusterDetails(data);
            setShowModal(true);
        } catch (error) {
            console.error('Error fetching cluster details:', error);
            setUploadMessage({status: 'error', message: error.message || 'クラスタ詳細の取得中にエラーが発生しました。'});
        }
    };

    // 履歴セッションがクリックされたときのハンドラー
    const handleHistorySessionClick = (sessionId) => {
        setCurrentSessionId(sessionId); // 表示するセッションIDを更新
        fetchAnalysisResults(sessionId); // そのセッションの分析結果をフェッチ
        setPath('/analysis'); // 分析結果表示に切り替える
        // window.history.pushState(null, '', `/history/${sessionId}`); // 必要に応じてURLを更新
    };

    // -- ルーティングロジック --
    // ブラウザのURLが変更されたときにpathステートを更新
    useEffect(() => {
        const handlePopState = () => {
            const currentPath = window.location.pathname;
            setPath(currentPath);
            const pathParts = currentPath.split('/');
            if (pathParts[1] === 'analysis' && pathParts[2]) { // /analysis/{id} のようなパスの場合
                setCurrentSessionId(parseInt(pathParts[2]));
                fetchAnalysisResults(parseInt(pathParts[2]));
            } else if (currentPath === '/') {
                setCurrentSessionId(null); // ホームは最新のセッションを表示
                fetchTimeSeriesData(); // ホームページは時系列データをフェッチ
            } else if (currentPath === '/history') {
                setCurrentSessionId(null); // 履歴ページは履歴リストのみフェッチ
                fetchAnalysisSessions();
            } else if (currentPath === '/analysis') { // /analysis (最新の分析結果を表示)
                setCurrentSessionId(null);
                fetchAnalysisResults();
            }
        };
        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, [fetchAnalysisResults, fetchAnalysisSessions, fetchTimeSeriesData]); // 依存配列に関数を追加

    // 初回ロード時にデータをフェッチ
    useEffect(() => {
        const pathParts = window.location.pathname.split('/');
        if (pathParts[1] === 'analysis' && pathParts[2]) {
            setCurrentSessionId(parseInt(pathParts[2]));
            fetchAnalysisResults(parseInt(pathParts[2]));
            setPath('/analysis');
        } else if (window.location.pathname === '/') {
            fetchTimeSeriesData(); // ホームページは時系列データをフェッチ
            fetchAnalysisSessions(); // 履歴リストもフェッチ
        } else if (window.location.pathname === '/history') {
            fetchAnalysisSessions(); // 履歴ページは履歴リストのみフェッチ
        } else if (window.location.pathname === '/analysis') {
            fetchAnalysisResults(); // 最新の分析結果をフェッチ
        }
    }, []); // 依存配列は空で初回のみ実行

    return (
        <>
            {/* サイドバーのレンダリング */}
            <div className="sidebar"> {/* id="sidebar-root-content" は削除し、直接 className="sidebar" を付与 */}
                <h5 className="card-title text-white mb-3">ナビゲーション</h5>
                <div className="nav flex-column nav-pills" role="tablist" aria-orientation="vertical">
                    <a href="/" className={`nav-link text-start ${path === '/' && !currentSessionId ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setPath('/'); window.history.pushState({}, '', '/'); setCurrentSessionId(null); }}>
                        ホーム (評価推移)
                    </a>
                    {/* ★★★ 「最新分析結果」ボタンを削除 ★★★ */}
                    {/* <a href="/analysis" className={`nav-link text-start ${path === '/analysis' && !currentSessionId ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setPath('/analysis'); window.history.pushState({}, '', '/analysis'); setCurrentSessionId(null); setActiveContent('pn_charts'); }}>
                        最新分析結果
                    </a> */}
                    
                    {/* currentSessionId が設定されている場合は、そのセッションの分析結果ページに飛ばす */}
                    {/* これを「分析履歴」ページ内でのクリックで遷移するように変更するため、ここからは削除 */}
                    {/* {(path === '/analysis' && currentSessionId) && (
                        <a href={`/analysis/${currentSessionId}`} className={`nav-link text-start active`} onClick={(e) => e.preventDefault()}>
                            履歴: {currentSessionId}
                        </a>
                    )} */}

                    <a href="/history" className={`nav-link text-start ${path === '/history' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setPath('/history'); window.history.pushState({}, '', '/history'); }}>
                        分析履歴
                    </a>
                </div>
                <hr className="text-white"/>
                <h5 className="card-title text-white mb-3 mt-3">アップロード</h5>
                <form onSubmit={handleFileUpload}>
                    <div className="input-group mb-3">
                        <input type="file" name="file" className="form-control form-control-sm" accept=".csv" required disabled={loadingUpload} />
                    </div>
                    <button type="submit" className="btn btn-primary btn-sm w-100" disabled={loadingUpload}>
                        {loadingUpload ? (
                            <>
                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                処理中...
                            </>
                        ) : (
                            "アップロード & 分析"
                        )}
                    </button>
                </form>
                {uploadMessage.message && (
                    <div className={`alert mt-3 p-2 ${uploadMessage.status === 'success' ? 'alert-success' : uploadMessage.status === 'error' ? 'alert-danger' : 'alert-info'}`} role="alert">
                        {uploadMessage.message}
                    </div>
                )}
            </div>

            {/* メインコンテンツのレンダリング */}
            <div className="main-content-wrapper"> {/* id="main-content-root-content" は削除し、直接 className="main-content-wrapper" を付与 */}
                {path === '/' && ( // ホームページ
                    <HomePage 
                        loadingAnalysis={loadingAnalysis}
                        loadingUpload={loadingUpload}
                        uploadMessage={uploadMessage}
                        handleFileUpload={handleFileUpload}
                        timeSeriesData={timeSeriesData}
                    />
                )}
                {/* /analysis/{id} の場合、または /analysis （最新）の場合も AnalysisPage を表示 */}
                {/* 履歴ページからの遷移もここで行う */}
                {(path.startsWith('/analysis') || (path === '/' && currentSessionId)) && (
                    <AnalysisPage
                        loadingAnalysis={loadingAnalysis}
                        uploadMessage={uploadMessage}
                        pnCharts={pnCharts}
                        topClusters={topClusters}
                        aiAnalysisComment={aiAnalysisComment}
                        onClusterClick={handleClusterClick}
                        activeContent={activeContent}
                        setActiveContent={setActiveContent}
                        currentSessionId={currentSessionId} 
                    />
                )}
                {path === '/history' && ( // 履歴ページ
                    <HistoryPage 
                        loadingHistory={loadingHistory}
                        analysisSessions={analysisSessions}
                        onSessionClick={handleHistorySessionClick}
                    />
                )}
                
                <CommentDetailsModal 
                    show={showModal} 
                    onClose={() => setShowModal(false)} 
                    clusterDetails={selectedClusterDetails} 
                />
            </div>
        </>
    );
}

// ReactアプリケーションをDOMにマウント
// index.html の #root に全体をマウント
const rootContainer = document.getElementById('root');
const root = createRoot(rootContainer);
root.render(createElement(App));