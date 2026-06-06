# 发布到 GitHub

## 1. 在 GitHub 创建空仓库

登录 https://github.com/new ，创建仓库（例如 `brain-memory`），**不要**勾选 README / .gitignore。

## 2. 推送代码

```powershell
cd D:\类脑记忆\cursor

# 替换为你的 GitHub 用户名和仓库名
$USER = "plusunm"
$REPO = "brain-memory"

git remote add origin "https://github.com/$USER/$REPO.git"
git push -u origin main
```

## 3. 上传 Release 包（可选）

在 GitHub 仓库页面 → Releases → Create a new release：

- Tag: `v5.0.0`
- Title: `Brain-Memory v5.0.0`
- 上传文件: `dist/brain-memory-5.0.0.zip`

## 4. 一键脚本（需已安装 gh 并完成 gh auth login）

```powershell
gh repo create brain-memory --public --source=. --remote=origin --push
gh release create v5.0.0 dist/brain-memory-5.0.0.zip --title "Brain-Memory v5.0.0"
```
