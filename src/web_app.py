"""
Web应用界面
提供股票分析系统的Web界面
"""
from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from datetime import datetime
from typing import Dict, Any, List
import logging

from src.stock_analysis_system import StockAnalysisSystem
from src.utils.batch_analyzer import BatchStockAnalyzer
from src.utils.monitor import StockMonitor

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 初始化系统组件
analysis_system = StockAnalysisSystem()
batch_analyzer = BatchStockAnalyzer()
monitor = StockMonitor()

# 全局变量
analysis_history = []
monitoring_status = {"active": False, "stocks": [], "rules": []}


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """分析单只股票"""
    try:
        data = request.get_json()
        company = data.get('company', '')
        ticker = data.get('ticker', '')

        if not company or not ticker:
            return jsonify({'success': False, 'error': '请提供公司名称和股票代码'})

        # 执行分析
        result = analysis_system.analyze_stock(company, ticker)

        # 添加到历史记录
        analysis_history.append({
            'company': company,
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'success': result['success']
        })

        # 保持历史记录在合理范围内
        if len(analysis_history) > 100:
            analysis_history[:] = analysis_history[-100:]

        return jsonify(result)

    except Exception as e:
        logger.error(f"分析股票失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/batch_analyze', methods=['POST'])
def batch_analyze():
    """批量分析"""
    try:
        data = request.get_json()
        stocks = data.get('stocks', [])
        strategy = data.get('strategy', 'parallel')

        if not stocks:
            return jsonify({'success': False, 'error': '请提供股票列表'})

        # 设置进度回调
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append(progress)

        batch_analyzer.set_progress_callback(progress_callback)

        # 执行批量分析
        result = batch_analyzer.analyze_multiple_stocks(stocks, strategy)

        # 添加进度更新到结果
        result['progress_updates'] = progress_updates

        return jsonify(result)

    except Exception as e:
        logger.error(f"批量分析失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/monitor/add_stock', methods=['POST'])
def add_monitor_stock():
    """添加监控股票"""
    try:
        data = request.get_json()
        company = data.get('company', '')
        ticker = data.get('ticker', '')
        interval = data.get('interval', 300)

        if not company or not ticker:
            return jsonify({'success': False, 'error': '请提供公司名称和股票代码'})

        success = monitor.add_stock_to_monitor(company, ticker, interval)

        if success:
            # 更新监控状态
            monitoring_status['stocks'].append({
                'company': company,
                'ticker': ticker,
                'interval': interval,
                'added_time': datetime.now().isoformat()
            })

        return jsonify({'success': success})

    except Exception as e:
        logger.error(f"添加监控股票失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/monitor/remove_stock', methods=['POST'])
def remove_monitor_stock():
    """移除监控股票"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '')

        if not ticker:
            return jsonify({'success': False, 'error': '请提供股票代码'})

        success = monitor.remove_stock_from_monitor(ticker)

        if success:
            # 更新监控状态
            monitoring_status['stocks'] = [
                s for s in monitoring_status['stocks'] if s['ticker'] != ticker
            ]

        return jsonify({'success': success})

    except Exception as e:
        logger.error(f"移除监控股票失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/monitor/add_rule', methods=['POST'])
def add_alert_rule():
    """添加预警规则"""
    try:
        data = request.get_json()
        rule_id = data.get('rule_id', '')
        ticker = data.get('ticker', '')
        rule_type = data.get('rule_type', '')
        condition = data.get('condition', '')
        threshold = data.get('threshold', 0)
        message = data.get('message', '')

        if not all([rule_id, ticker, rule_type, condition, message]):
            return jsonify({'success': False, 'error': '请提供完整的规则信息'})

        success = monitor.add_alert_rule(rule_id, ticker, rule_type, condition, threshold, message)

        if success:
            # 更新监控状态
            monitoring_status['rules'].append({
                'rule_id': rule_id,
                'ticker': ticker,
                'rule_type': rule_type,
                'condition': condition,
                'threshold': threshold,
                'message': message,
                'created_time': datetime.now().isoformat()
            })

        return jsonify({'success': success})

    except Exception as e:
        logger.error(f"添加预警规则失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/monitor/start', methods=['POST'])
def start_monitoring():
    """启动监控"""
    try:
        data = request.get_json()
        interval = data.get('interval', 300)

        monitor.start_monitoring(interval)
        monitoring_status['active'] = True

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"启动监控失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/monitor/stop', methods=['POST'])
def stop_monitoring():
    """停止监控"""
    try:
        monitor.stop_monitoring()
        monitoring_status['active'] = False

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"停止监控失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/monitor/status')
def get_monitor_status():
    """获取监控状态"""
    try:
        status = monitor.get_monitoring_status()
        return jsonify({
            'status': status,
            'config': monitoring_status
        })
    except Exception as e:
        logger.error(f"获取监控状态失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/history')
def get_history():
    """获取分析历史"""
    try:
        limit = request.args.get('limit', 50, type=int)
        return jsonify({
            'success': True,
            'history': analysis_history[-limit:]
        })
    except Exception as e:
        logger.error(f"获取分析历史失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/export/<export_type>')
def export_data(export_type):
    """导出数据"""
    try:
        if export_type == 'json':
            return jsonify({
                'history': analysis_history,
                'monitoring_status': monitoring_status,
                'export_time': datetime.now().isoformat()
            })
        elif export_type == 'csv':
            import pandas as pd
            df = pd.DataFrame(analysis_history)
            csv_data = df.to_csv(index=False)
            return csv_data, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename="analysis_history.csv"'
            }
        else:
            return jsonify({'success': False, 'error': '不支持的导出格式'})

    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/reports/<filename>')
def get_report(filename):
    """获取报告文件"""
    try:
        return send_file(f'reports/{filename}', as_attachment=True)
    except Exception as e:
        logger.error(f"获取报告文件失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


def create_templates():
    """创建HTML模板"""
    os.makedirs('templates', exist_ok=True)

    # 首页模板
    index_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票分析系统</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 2px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid #ddd;
            border-bottom: none;
            background-color: #f9f9f9;
            margin-right: 5px;
        }
        .tab.active {
            background-color: white;
            border-bottom: 2px solid white;
            margin-bottom: -2px;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, select, textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        .progress {
            width: 100%;
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-bar {
            height: 100%;
            background-color: #007bff;
            transition: width 0.3s ease;
        }
        .error {
            color: #dc3545;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .success {
            color: #155724;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .stock-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stock-item {
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        .monitoring-status {
            margin-top: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #e7f3ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 股票分析系统</h1>
            <p>基于AI的智能股票分析和监控平台</p>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="showTab('single')">单股票分析</div>
            <div class="tab" onclick="showTab('batch')">批量分析</div>
            <div class="tab" onclick="showTab('monitor')">实时监控</div>
            <div class="tab" onclick="showTab('history')">分析历史</div>
        </div>

        <!-- 单股票分析 -->
        <div id="single" class="tab-content active">
            <h2>单股票分析</h2>
            <form id="singleForm">
                <div class="form-group">
                    <label for="company">公司名称:</label>
                    <input type="text" id="company" name="company" required placeholder="例如：苹果公司">
                </div>
                <div class="form-group">
                    <label for="ticker">股票代码:</label>
                    <input type="text" id="ticker" name="ticker" required placeholder="例如：AAPL">
                </div>
                <button type="submit">开始分析</button>
            </form>
            <div id="singleResult"></div>
        </div>

        <!-- 批量分析 -->
        <div id="batch" class="tab-content">
            <h2>批量分析</h2>
            <form id="batchForm">
                <div class="form-group">
                    <label for="stocks">股票列表 (JSON格式):</label>
                    <textarea id="stocks" name="stocks" rows="6" placeholder='[{"company": "苹果公司", "ticker": "AAPL"}, {"company": "微软", "ticker": "MSFT"}]'></textarea>
                </div>
                <div class="form-group">
                    <label for="strategy">分析策略:</label>
                    <select id="strategy" name="strategy">
                        <option value="parallel">并行分析</option>
                        <option value="sequential">顺序分析</option>
                        <option value="adaptive">自适应分析</option>
                    </select>
                </div>
                <button type="submit">开始批量分析</button>
            </form>
            <div id="batchProgress"></div>
            <div id="batchResult"></div>
        </div>

        <!-- 实时监控 -->
        <div id="monitor" class="tab-content">
            <h2>实时监控</h2>
            <div class="monitoring-status">
                <h3>监控状态</h3>
                <div id="monitorStatus">未启动</div>
                <button onclick="toggleMonitoring()">启动/停止监控</button>
            </div>

            <h3>添加监控股票</h3>
            <form id="monitorForm">
                <div class="form-group">
                    <label for="monitorCompany">公司名称:</label>
                    <input type="text" id="monitorCompany" name="company" required>
                </div>
                <div class="form-group">
                    <label for="monitorTicker">股票代码:</label>
                    <input type="text" id="monitorTicker" name="ticker" required>
                </div>
                <div class="form-group">
                    <label for="interval">检查间隔 (秒):</label>
                    <input type="number" id="interval" name="interval" value="300" min="60">
                </div>
                <button type="submit">添加到监控</button>
            </form>

            <h3>添加预警规则</h3>
            <form id="ruleForm">
                <div class="form-group">
                    <label for="ruleId">规则ID:</label>
                    <input type="text" id="ruleId" name="rule_id" required>
                </div>
                <div class="form-group">
                    <label for="ruleTicker">股票代码:</label>
                    <input type="text" id="ruleTicker" name="ticker" required>
                </div>
                <div class="form-group">
                    <label for="ruleType">规则类型:</label>
                    <select id="ruleType" name="rule_type">
                        <option value="price">价格预警</option>
                        <option value="score">评分预警</option>
                        <option value="rating_change">评级变化</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="condition">条件:</label>
                    <select id="condition" name="condition">
                        <option value="above">高于</option>
                        <option value="below">低于</option>
                        <option value="equal">等于</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="threshold">阈值:</label>
                    <input type="number" id="threshold" name="threshold" step="0.01" required>
                </div>
                <div class="form-group">
                    <label for="message">预警消息:</label>
                    <input type="text" id="message" name="message" required>
                </div>
                <button type="submit">添加规则</button>
            </form>
        </div>

        <!-- 分析历史 -->
        <div id="history" class="tab-content">
            <h2>分析历史</h2>
            <button onclick="loadHistory()">刷新历史</button>
            <div id="historyList"></div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // 隐藏所有标签内容
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            // 显示选中的标签
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        // 单股票分析
        document.getElementById('singleForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);

            fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('singleResult');
                if (data.success) {
                    resultDiv.innerHTML = `
                        <div class="success">
                            <h3>分析成功！</h3>
                            <p><strong>公司:</strong> ${data.company}</p>
                            <p><strong>股票代码:</strong> ${data.ticker}</p>
                            <p><strong>投资评级:</strong> ${data.investment_rating.rating}</p>
                            <p><strong>综合评分:</strong> ${data.overall_score.toFixed(1)}/100</p>
                            <p><strong>报告路径:</strong> ${data.report_path}</p>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="error">分析失败: ${data.error}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('singleResult').innerHTML = `<div class="error">请求失败: ${error}</div>`;
            });
        });

        // 批量分析
        document.getElementById('batchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.stocks = JSON.parse(data.stocks);

            const progressDiv = document.getElementById('batchProgress');
            const resultDiv = document.getElementById('batchResult');

            progressDiv.innerHTML = '<div class="progress"><div class="progress-bar" style="width: 0%"></div></div>';

            fetch('/batch_analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    resultDiv.innerHTML = `
                        <div class="success">
                            <h3>批量分析完成！</h3>
                            <p><strong>总计:</strong> ${data.total_count}</p>
                            <p><strong>成功:</strong> ${data.success_count}</p>
                            <p><strong>失败:</strong> ${data.failed_count}</p>
                            <p><strong>成功率:</strong> ${data.success_rate.toFixed(1)}%</p>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="error">批量分析失败: ${data.error}</div>`;
                }
            })
            .catch(error => {
                resultDiv.innerHTML = `<div class="error">请求失败: ${error}</div>`;
            });
        });

        // 监控相关功能
        function toggleMonitoring() {
            const isActive = document.getElementById('monitorStatus').textContent.includes('运行中');
            const endpoint = isActive ? '/monitor/stop' : '/monitor/start';

            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({interval: 300})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateMonitorStatus();
                }
            });
        }

        function updateMonitorStatus() {
            fetch('/monitor/status')
            .then(response => response.json())
            .then(data => {
                const statusDiv = document.getElementById('monitorStatus');
                if (data.status.monitoring) {
                    statusDiv.innerHTML = `
                        <p><strong>状态:</strong> 运行中</p>
                        <p><strong>监控股票数:</strong> ${data.status.monitored_stocks}</p>
                        <p><strong>预警规则数:</strong> ${data.status.alert_rules}</p>
                        <p><strong>监控间隔:</strong> ${data.status.monitoring_interval}秒</p>
                    `;
                } else {
                    statusDiv.innerHTML = '<p><strong>状态:</strong> 未启动</p>';
                }
            });
        }

        // 添加监控股票
        document.getElementById('monitorForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);

            fetch('/monitor/add_stock', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('股票已添加到监控列表');
                } else {
                    alert('添加失败: ' + data.error);
                }
            });
        });

        // 加载历史记录
        function loadHistory() {
            fetch('/history')
            .then(response => response.json())
            .then(data => {
                const historyDiv = document.getElementById('historyList');
                if (data.success) {
                    let html = '<div class="stock-list">';
                    data.history.forEach(item => {
                        html += `
                            <div class="stock-item">
                                <h4>${item.company} (${item.ticker})</h4>
                                <p><strong>时间:</strong> ${item.timestamp}</p>
                                <p><strong>状态:</strong> ${item.success ? '成功' : '失败'}</p>
                            </div>
                        `;
                    });
                    html += '</div>';
                    historyDiv.innerHTML = html;
                } else {
                    historyDiv.innerHTML = '<div class="error">加载历史失败</div>';
                }
            });
        }

        // 定期更新监控状态
        setInterval(updateMonitorStatus, 30000);
    </script>
</body>
</html>
    """

    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)

    logger.info("HTML模板已创建")


if __name__ == '__main__':
    # 创建模板
    create_templates()

    # 启动Web应用
    print("启动Web应用...")
    print("访问地址: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)