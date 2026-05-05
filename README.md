<<<<<<< HEAD
# 🔧 NetCluster - Distributed Network Security Platform

A powerful Python-based desktop application for distributed network security testing and penetration testing operations. NetCluster features a Master-Worker architecture that enables coordinated attack deployment across multiple nodes.

![NetCluster Logo](https://img.shields.io/badge/NetCluster-Distributed%20Security-blue?style=for-the-badge&logo=shield)

## 🌟 Features

### 🎯 Master Node
- **Central Control Interface**: PyQt5-based GUI for attack management
- **Attack Deployment**: Deploy Brute Force and DoS attacks
- **Real-time Monitoring**: Live logs and attack results
- **Worker Node Management**: Connect and manage multiple worker nodes
- **Task Distribution**: Automatically distribute tasks across worker nodes
- **Settings Synchronization**: Broadcast settings to all connected workers

### ⚡ Worker Node
- **Simple Connection Interface**: Easy connection to Master Node via PIN
- **Task Execution**: Execute distributed attack tasks
- **Real-time Feedback**: Send progress updates to Master
- **Settings Mirroring**: Automatically apply Master Node settings
- **Auto-reconnect**: Automatic reconnection on connection loss

### 🔒 Security Features
- **PIN-based Authentication**: Secure worker node connections
- **Encrypted Communication**: TCP-based secure messaging
- **Connection Validation**: Real-time connection status monitoring
- **Graceful Disconnection**: Proper cleanup on node disconnection

## 📋 Requirements

### System Requirements
- **OS**: Windows 10/11, macOS, or Linux
- **Python**: 3.7 or higher
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 100MB free space

### Python Dependencies
```
PyQt5==5.15.9
paramiko==3.3.1
scapy==2.5.0
colorama==0.4.6
```

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/NetCluster.git
cd NetCluster
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python NetClusterApp.py
```

## 📁 Project Structure

```
NetCluster/
├── NetClusterApp.py          # Main launcher application
├── MasterNode.py             # Master Node GUI and logic
├── WorkerNode.py             # Worker Node GUI and logic
├── utils/
│   └── network.py            # Network communication utilities
├── attacks/                  # Attack modules (future)
├── wordlists/               # Password wordlists (future)
├── assets/                  # GUI assets and icons
└── README.md               # This file
```

## 🎮 Usage Guide

### Starting the Application

1. **Launch NetCluster**:
   ```bash
   python NetClusterApp.py
   ```

2. **Choose Node Type**:
   - Click **🎯 Master Node** to start the central controller
   - Click **⚡ Worker Node** to start a worker node

### Master Node Operation

#### 1. Initial Setup
- The Master Node generates a unique **6-digit PIN**
- Display this PIN to worker nodes for connection
- PIN can be regenerated using the "Regenerate PIN" button

#### 2. Attack Deployment
1. **Navigate to "Available Attacks"**
2. **Select Attack Type**:
   - **BruteForce Attack**: SSH/Password brute force
   - **DoS Attack**: Denial of Service (SYN/UDP/ICMP flood)
3. **Click "Deploy"** to configure the attack

#### 3. Attack Configuration
Navigate to **"Attack Dashboard"** to configure:

**BruteForce Attack Settings**:
- Target IP/Domain
- Port (default: 22)
- Protocol (SSH, FTP, HTTP)
- Username/Email
- Attack Type (Dictionary, Incremental, Hybrid)
- Wordlist Upload
- Number of Threads
- Timeout (seconds)

**DoS Attack Settings**:
- Target IP/Domain
- Port (default: 80)
- Attack Method (TCP Flood, UDP Flood, HTTP Flood, SYN Flood)
- Number of Threads
- Packet Size (bytes)
- Interval (milliseconds)
- Attack Duration (seconds)

#### 4. Attack Control
- **Start Attack**: Begin the configured attack
- **Stop Attack**: Halt the running attack
- **Distribute**: Distribute tasks to connected worker nodes

#### 5. Monitoring
- **Attack Results**: Real-time attack progress and results
- **Master Node Logs**: System activity and worker node communications
- **Worker Count**: Number of connected worker nodes

### Worker Node Operation

#### 1. Connection Setup
1. **Enter Master PIN**: Input the 6-digit PIN from Master Node
2. **Click "Connect"**: Establish connection to Master Node
3. **Monitor Status**: Check connection status indicator

#### 2. Task Execution
- Worker nodes automatically receive and execute distributed tasks
- Real-time progress updates sent to Master Node
- Automatic task acknowledgment and execution

#### 3. Settings Synchronization
- **Theme Mode**: Automatically syncs with Master Node
- **Brightness**: Adjusts based on Master Node settings
- **Font Size**: Updates to match Master Node configuration

## ⚙️ Settings

### Master Node Settings
- **Theme Mode**: Dark/Light theme selection
- **Screen Brightness**: Adjust window opacity (30-100%)
- **Font Size**: Terminal font size (8-32px)
- **Worker Node Connection Limit**: Maximum connected workers (1-100)

### Settings Broadcasting
All Master Node settings are automatically broadcast to connected worker nodes:
- Theme changes apply immediately
- Brightness adjustments sync across nodes
- Font size updates propagate to all workers

## 🔧 Technical Details

### Network Architecture
- **Master Node**: Central controller with GUI interface
- **Worker Nodes**: Distributed execution nodes
- **Communication**: TCP sockets with JSON messaging
- **Ports**: 
  - Master PIN Server: 50051
  - Log Broadcast Server: 50050

### Attack Types

#### BruteForce Attack
- **Purpose**: Password cracking and credential testing
- **Protocols**: SSH, FTP, HTTP
- **Methods**: Dictionary, Incremental, Hybrid
- **Features**: Wordlist upload, configurable threads, timeout settings

#### DoS Attack
- **Purpose**: Denial of Service testing
- **Methods**: TCP Flood, UDP Flood, HTTP Flood, SYN Flood
- **Features**: Configurable packet size, interval, duration

### Security Considerations
- **PIN Authentication**: 6-digit numeric PIN for worker connections
- **Connection Validation**: Real-time connection status monitoring
- **Graceful Disconnection**: Proper cleanup on connection loss
- **Mock Mode**: Safe testing without actual network impact

## 🐛 Troubleshooting

### Common Issues

#### Connection Problems
- **Worker can't connect**: Verify PIN is correct and Master Node is running
- **Connection drops**: Check network connectivity and firewall settings
- **PIN not working**: Regenerate PIN on Master Node

#### GUI Issues
- **Buttons not visible**: Restart the application
- **CSS warnings**: These are cosmetic and don't affect functionality
- **Window scaling**: Adjust Qt environment variables if needed

#### Performance Issues
- **Slow response**: Reduce number of worker nodes
- **High CPU usage**: Lower thread count in attack settings
- **Memory issues**: Close unused worker nodes

### Error Messages
- `[ERROR] No attack selected`: Deploy an attack before starting
- `[WARNING] No worker nodes connected`: Start worker nodes first
- `[INFO] Task distribution completed`: Normal operation message

## 🔮 Future Enhancements

### Planned Features
- **Additional Attack Types**: SQL injection, XSS, CSRF testing
- **Advanced Task Distribution**: Load balancing and failover
- **Result Aggregation**: Centralized result collection and analysis
- **Attack Templates**: Pre-configured attack profiles
- **Reporting**: PDF/HTML attack reports
- **API Integration**: REST API for external tools

### Technical Improvements
- **Encryption**: End-to-end encryption for communications
- **Authentication**: Certificate-based authentication
- **Scalability**: Support for hundreds of worker nodes
- **Persistence**: Attack history and configuration storage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**IMPORTANT**: This tool is designed for educational and authorized security testing purposes only. Users are responsible for ensuring they have proper authorization before testing any systems or networks. The developers are not responsible for any misuse of this software.

### Legal Compliance
- Only use on systems you own or have explicit permission to test
- Comply with local and international laws regarding network security testing
- Obtain proper authorization before conducting any security assessments
- Respect privacy and data protection regulations

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### How to Contribute
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

### Getting Help
- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join our community discussions

### Contact Information
- **GitHub**: [NetCluster Repository](https://github.com/yourusername/NetCluster)
- **Email**: support@netcluster.com
- **Discord**: [NetCluster Community](https://discord.gg/netcluster)

## 🙏 Acknowledgments

- **PyQt5 Team**: For the excellent GUI framework
- **Paramiko Developers**: For SSH library support
- **Scapy Contributors**: For network packet manipulation
- **Open Source Community**: For inspiration and support

---

**🔧 NetCluster** - Empowering distributed network security testing with ease and precision.

*Built with ❤️ for the security community* 

## MasterNode & WorkerNode Connection Protocol

NetCluster uses a two-step TCP socket protocol to securely connect WorkerNodes to the MasterNode, authenticate them using a PIN, and stream logs and commands.

### 1. Connection Protocol

- **Sockets:** TCP
- **Ports:**
  - **50051:** PIN authentication
  - **50050:** Log streaming and worker registration

### 2. Connection Flow

#### A. WorkerNode → MasterNode

1. **User Input:**  
   Worker enters Master PIN and Master IP in the WorkerNode GUI.

2. **PIN Check:**  
   - WorkerNode connects to MasterNode at port 50051.
   - Sends the PIN.
   - MasterNode checks the PIN and replies:
     - `OK` if correct
     - `FAIL` if incorrect
   - WorkerNode proceeds only if `OK`.

3. **Log Client Connection:**  
   - WorkerNode connects to MasterNode at port 50050.
   - Sends its worker name.
   - Receives logs and status updates.

#### B. MasterNode Side

- **PIN Server:**  
  Listens on 50051, checks PINs, replies with `OK`/`FAIL`.
- **LogBroadcastServer:**  
  Listens on 50050, tracks workers, broadcasts logs.

### 3. Worker Identification

- WorkerNode sends its name on connection.
- MasterNode tracks name, IP, and status.

### 4. Disconnection

- If MasterNode PIN is regenerated, it sends `[PIN_CHANGED]` to all workers.
- WorkerNodes disconnect and prompt for the new PIN.

### 5. Connection Sequence Table

| Step           | WorkerNode Action                | MasterNode Action                | Port   |
|----------------|----------------------------------|----------------------------------|--------|
| PIN Check      | Send PIN                         | Validate, reply OK/FAIL          | 50051  |
| Log Connection | Connect, send name, receive logs | Accept, track, broadcast logs    | 50050  |
| PIN Change     | Disconnect on `[PIN_CHANGED]`    | Broadcast `[PIN_CHANGED]`        | 50050  |

### 6. Security Notes

- Only nodes with the correct PIN can connect.
- PIN changes force all workers to re-authenticate. 
=======
# NetCluster
Collage Group Major Project , NetCluster is a multi-computing desktop software that connects multiple machines to work together as a unified system. It enables distributed task execution, real-time monitoring, and cluster-based resource management through a modern PyQt-powered interface.
>>>>>>> 3f88d85c5350926458e193f0f6a8903809794192
