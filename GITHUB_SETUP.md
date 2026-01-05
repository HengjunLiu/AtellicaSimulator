# GitHub 访问配置说明

## 问题

推送到远程仓库时遇到权限错误：
```
remote: Permission to HengjunLiu/AtellicaSimulator.git denied to zhangxuedong-create.
fatal: unable to access 'https://github.com/HengjunLiu/AtellicaSimulator/': The requested URL returned error: 403
```

## 解决方案

### 方案1: 使用Personal Access Token (推荐)

#### 步骤1: 生成Personal Access Token
1. 访问 GitHub → Settings → Developer settings → Personal access tokens
2. 点击 "Generate new token (classic)"
3. 设置名称（如 "AtellicaSimulator"）
4. 选择权限:
   - ✅ repo (完整控制私有仓库)
5. 点击 "Generate token"
6. **复制生成的token**（格式: ghp_xxxxxxxxxxxx）

#### 步骤2: 配置Git使用token
```bash
# 方式1: 修改remote URL（临时）
git remote set-url origin https://<TOKEN>@github.com/HengjunLiu/AtellicaSimulator.git

# 方式2: 使用credential helper（推荐）
git config --global credential.helper store
# 下次推送时会提示输入用户名和密码，输入:
# 用户名: 你的GitHub用户名
# 密码: 刚才生成的token
```

#### 步骤3: 重新推送
```bash
git push origin main
```

---

### 方案2: 使用SSH密钥

#### 步骤1: 检查现有SSH密钥
```bash
ls ~/.ssh/
```
如果看到 `id_rsa` 和 `id_rsa.pub`，说明已有SSH密钥。

#### 步骤2: 生成新SSH密钥（如果没有）
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

#### 步骤3: 添加SSH密钥到GitHub
1. 复制公钥内容：
```bash
cat ~/.ssh/id_rsa.pub
# 或
cat ~/.ssh/id_ed25519.pub
```
2. 访问 GitHub → Settings → SSH and GPG keys → New SSH key
3. 粘贴公钥内容，保存

#### 步骤4: 修改仓库URL为SSH
```bash
git remote set-url origin git@github.com:HengjunLiu/AtellicaSimulator.git
```

#### 步骤5: 验证连接
```bash
ssh -T git@github.com
```

#### 步骤6: 重新推送
```bash
git push origin main
```

---

### 方案3: 使用GitHub CLI

#### 安装GitHub CLI
```bash
# Windows (使用chocolatey)
choco install gh

# 或使用winget
winget install GitHub.cli
```

#### 认证
```bash
gh auth login
# 选择 GitHub.com
# 选择 HTTPS
# 输入Personal Access Token
```

#### 重新推送
```bash
git push origin main
```

---

## 验证推送结果

无论使用哪种方案，成功后可以看到类似输出：
```
Enumerating objects: 19, done.
Counting objects: 100% (19/19), done.
Writing objects: 100% (19/19), 82.56 KiB | 2.58 MiB/s, done.
To https://github.com/HengjunLiu/AtellicaSimulator.git
   8700593..1479ad8  main -> main
```

---

## 当前提交信息

已成功创建提交：
- **Commit ID**: `1479ad8`
- **分支**: `main`
- **消息**: 
```
feat: Complete URAP protocol implementation

✨ URAP Protocol Enhancement (v1.1.0)

Core Features:
- Implement KEEPALIVE instruction (0x0005) with automatic timeout detection
- Implement Load_Unload Command (0x0303/0x0304) with full status codes
- Implement Transfer Status (0x0209/0x020A)
- Implement Add/Skip/Clear Queue commands (0x0401-0x0406)
- Add queue management system with carrier locking
- Add sample transfer processing logic

Technical Changes:
- Added 12 new message type constants
- Added 7 new core methods for queue management
- Added process_load_unload() with complete status handling
- Enhanced las.py with 415 lines of new code
- Enhanced core.py with 218 lines of new code
- Added comprehensive test suite (test_urap_commands.py)
- Added CHANGELOG.md for version history
```

提交已保存在本地Git仓库，推送成功后所有更改将同步到GitHub。

---

## 联系仓库所有者

如果以上方案都无法解决，可能需要：
1. 联系仓库所有者 `HengjunLiu`
2. 请求将你的GitHub账户添加到仓库协作者列表
3. 或者请仓库所有者帮你推送这次更改

---

## 后续步骤

1. 配置好访问权限后，运行：
   ```bash
   git push origin main
   ```

2. 验证推送结果：
   ```bash
   git log --oneline -3
   ```

3. 在GitHub上查看提交记录和更改

---

**提示**: 推荐使用 **方案1 (Personal Access Token)**，这是最简单且安全的方法。
