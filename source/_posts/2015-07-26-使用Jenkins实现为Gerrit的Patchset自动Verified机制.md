title: 使用Jenkins实现为Gerrit的Patchset自动Verified机制
id: jenkins-gerrit-verified
date: 2015-07-26 14:39:47
tags:
---
## 背景

Gerrit是一款优秀的Code Review工具，提供了一套完整的Git工作流，有别于`gitflow`等其他工作流，Gerrit的思想是必须是验证过、Review过、测试过的代码才能够合并到代码库中。

## 配置Gerrit

“Label Verified”功能从Gerrit 2.7版本起不再是默认开启，故需要在项目配置中开启 “Label Verified” 功能。

Gerrit将每个项目的配置信息存储在项目的`refs/meta/config`分支中，
为方便起见，我们把所有项目的Verified功能开启，这里需要修改`All-Projects`的配置信息，
如果想对特定项目进行单独配置，只需要处理特定的项目的配置信息即可。

将`All-Projects`的`refs/meta/config`分支拉下来，修改`project.config`文件。


```sh
git clone ssh://user@host:29418/All-Projects
cd All-Projects
git fetch origin refs/meta/config:refs/remotes/origin/meta/config
git checkout meta/config
```

在文件的底部加上

```
[label "Verified"]
    function = MaxWithBlock
    value = -1 Fails
    value =  0 No score
    value = +1 Verified
```

提交并push到远端，使其生效。

```sh
git add -u
git ci -m 'Add Label Verified'
git push origin meta/config:meta/config
```

此时，会在后台中`Projects` > `Access`中看到下面的“Label Verified”已经出现在 "Add Permission..." 下拉菜单中了。

![Verified已经出现在Permission下拉菜单中了](/images/jenkins-gerrit-verified/1.png)

## 配置Jenkins

### “Gerrit Trigger”插件 安装和配置

Jenkins插件管理中安装“Gerrit Trigger”插件。

![Jenkins插件管理中安装“Gerrit Trigger”插件。](/images/jenkins-gerrit-verified/2.png)

安装完毕后，会在“系统设置”页面出现“Gerrit Trigger”的配置项。

![“Gerrit Trigger”的配置项](/images/jenkins-gerrit-verified/3.png)

进入“Gerrit Trigger”配置页面，点击左侧菜单的 “Add New Server” 来添加“Gerrit 服务器”。

![添加“Gerrit 服务器”](/images/jenkins-gerrit-verified/4.png)

根据实际情况，配置“Gerrit 服务器”信息。

### 新建项目

进入“新建项目”页面，选择“构建一个自由风格的软件项目”，“源码管理”选择“None”，“构建触发器”选择“Gerrit Trigger”，
“Gerrit Trigger”配置项中，“Trigger on”增加“Patchset Created”，
“Specify what Gerrit project(s) to trigger a build on.”中增加项目和Branch pattern。

![“构建触发器”配置](/images/jenkins-gerrit-verified/5.png)

## 用户配置

Jenkins需要一个Gerrit用户来与Gerrit通讯，这个用户的权限也需要配置一下。

### “Non-Interactive Users”组

Gerrit内置有个用户组 “Non-Interactive Users”组，这个组的用户可以批量执行动作，`All-Projects`里权限设置如下。

```
[capability]
	administrateServer = group Administrators
	priority = batch group Non-Interactive Users
	streamEvents = group Non-Interactive Users
```

把Jenkins用户加到这个组里。

### 赋予Jenkins用户“Label Verified”权限

```
[access "refs/heads/*"]
	create = group Administrators
	create = group Project Owners
	forgeAuthor = group Registered Users
	forgeCommitter = group Administrators
	forgeCommitter = group Project Owners
	push = group Administrators
	push = group Project Owners
	label-Code-Review = -2..+2 group Administrators
	label-Code-Review = -2..+2 group Project Owners
	label-Code-Review = -1..+1 group Registered Users
	submit = group Administrators
	submit = group Project Owners
	editTopicName = +force group Administrators
	editTopicName = +force group Project Owners
	label-Verified = -1..+1 group Non-Interactive Users  # 赋予Jenkins用户“Label Verified”权限
```

## 编写构建脚本

Jenkins的“Gerrit Trigger”中参数列表可以参考下图

![“Gerrit Trigger”中参数列表](/images/jenkins-gerrit-verified/7.png)

可在构建脚本中使用这些参数，常用的参数有： GERRIT_REFSPEC， GERRIT_PROJECT。

```
PY_FILES=`git diff --diff-filter=ACM --name-only HEAD^.. | egrep \\.py$`
if [[ $? -eq 0 ]]
then
    ${PEP8} ${PY_FILES} >&2

    # Capture the exit status of last command
    EXIT_CODE=$?

    # If the EXIT_CODE is not 0 fail
    if [[ $EXIT_CODE -ne 0 ]]
    then
      echo "EXIST UNCLEAN CODE, PLEASE MODIFY YOUR CODE TO FIT REQUIRE!!!"
      echo "##############################"
      exit $EXIT_CODE
    fi
fi
```
