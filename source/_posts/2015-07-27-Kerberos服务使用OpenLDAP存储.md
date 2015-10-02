title: Kerberos服务使用OpenLDAP存储
date: 2015-07-27 21:33:22
tags:
id: openldap-kerberos
---

## 背景

### 什么是`OpenLDAP`，它用来做什么？

### 什么是`Kerberos`，它用来做什么？

### 为什么要同时使用`OpenLDAP`和`Kerberos`呢？

### 我们的目标是什么？

## OpenLDAP服务器

### 安装OpenLDAP服务器

```sh
apt-get install -y slapd ldap-utils krb5-kdc-ldap
```

### 将`kerberos schema`需要添加到`cn=config`树中

1. 新增配置文件`schema_convert.conf`，输入下面的内容。
    ```
    include /etc/ldap/schema/core.schema
    include /etc/ldap/schema/collective.schema
    include /etc/ldap/schema/corba.schema
    include /etc/ldap/schema/cosine.schema
    include /etc/ldap/schema/duaconf.schema
    include /etc/ldap/schema/dyngroup.schema
    include /etc/ldap/schema/inetorgperson.schema
    include /etc/ldap/schema/java.schema
    include /etc/ldap/schema/misc.schema
    include /etc/ldap/schema/nis.schema
    include /etc/ldap/schema/openldap.schema
    include /etc/ldap/schema/ppolicy.schema
    include /etc/ldap/schema/kerberos.schema
    ```

2. 创建临时目录，用来存放LDIF文件
    ```
    mkdir /tmp/ldif_output
    ```

3. 使用`slapcat`命令转换上面指定的schema文件
    ```
    slapcat -f schema_convert.conf -F /tmp/ldif_output -n0 -s \
    "cn={12}kerberos,cn=schema,cn=config" > /tmp/cn=kerberos.ldif
    ```

4. 修改生成的`/tpm/cn\=kerberos.ldif`文件，找到并修改下面的两行：
    ```
    dn: cn=kerberos,cn=schema,cn=config
    ...
    cn: kerberos
    ```
    另外，还需要移除位于文件末位的下面几行：
    ```
    structuralObjectClass: olcSchemaConfig
    entryUUID: 18ccd010-746b-102d-9fbe-3760cca765dc
    creatorsName: cn=config
    createTimestamp: 20090111203515Z
    entryCSN: 20090111203515.326445Z#000000#000#000000
    modifiersName: cn=config
    modifyTimestamp: 20090111203515Z
    ```

5. 使用`slapadd`命令加载新的schema
    ```sh
    ldapadd -Q -Y EXTERNAL -H ldapi:/// -f /tmp/cn\=kerberos.ldif
    ```

6. 为`krbPrincipalName`属性增加索引
    ```sh
ldapmodify -Q -Y EXTERNAL -H ldapi:/// <<EOF
dn: olcDatabase={1}hdb,cn=config
add: olcDbIndex
olcDbIndex: krbPrincipalName eq,pres,sub
EOF
```

7. 最后，更新访问控制清单(ACL)
    ```sh
    ldapmodify -Q -Y EXTERNAL -H ldapi:///
    Enter LDAP Password:
    dn: olcDatabase={1}hdb,cn=config
    replace: olcAccess
    olcAccess: to attrs=userPassword,shadowLastChange,krbPrincipalKey by
     dn="cn=admin,dc=example,dc=com" write by anonymous auth by self write by * none
    -
    add: olcAccess
    olcAccess: to dn.base="" by * read
    -
    add: olcAccess
    olcAccess: to * by dn="cn=admin,dc=example,dc=com" write by * read

    modifying entry "olcDatabase={1}hdb,cn=config"
    ```

## Kerberos安装


krb5-user krb5-kdc krb5-admin-server krb5-kdc-ldap

Kerberos krb5-kdc程序有BUG，如果使用类型`cn=kdc,cn=kerberos,dc=7v1,dc=net`等作为查询DN的话，
会出现崩溃，所以直接使用`RootDN`来搞啦。

### TIPS

1. 一些`Principal`惯例
    1. `host/${hostname}`表示一台机器。
    2. `ldap/${hostname}`表示一个`ldap`服务。
    3. `${username}/admin`会在kadmin里使用。
4. `kadmin`、`kpasswd`会连接`krb5-admin-server`服务，需先在服务器端开启`kadmind`服务。
5. `kadmind`程序启动的时候需要进行`Seeding random number generator`，如果机器上IO比较少，
生成过程非常缓慢，系统无法初始化完成，客户端调用`kadmin`服务是会报出
`kpasswd: Cannot contact any KDC for requested realm changing password`错误。
注意观察日志文件中下面两行内容：
    ```
    Jul 28 11:35:51 bbdb76488f37 kadmind[443](info): Seeding random number generator
    Jul 28 11:38:49 bbdb76488f37 kadmind[443](info): starting
    ```
    如果特别缓慢，可以使用`ping -f $HOSTNAME`命令产生随机IO。

## saslauthd

### 配置`saslauthd`

1. 修改配置文件`/etc/default/saslauthd`
    ```
    START=yes
    DESC="SASL Authentication Daemon"
    NAME="saslauthd"
    MECHANISMS="kerberos5"
    MECH_OPTIONS=""
    THREADS=5
    OPTIONS="-c -m /var/run/saslauthd"
    ```

2. 为`openldap`账号添加读权限
    ```sh
    sudo adduser openldap sasl
    ```

3. 为本机生成kerberos授权
    ```
kadmin.local -q "ank -randkey host/`hostname`"
kadmin.local -q "ktadd host/`hostname`"
```

4. 测试
   ```sh
   testsaslauthd -u test -p 123456

   ```

### 配置`openldap`和`kerberos`

1. 需要先把`/etc/krb5.conf`拷一份到`openldap`服务器。
2. 在`kerberos`中为`openldap`服务器添加`princ`。
    ```sh
kadmin.local -q "ank -randkey ldap/`hostname`"
kadmin.local -q "ktadd ldap/`hostname`"
```
3. 新增`/etc/ldap/sals2/slapd.conf`，增加下面内容：
    ```
    pwcheck_method: saslauthd
    mech_list: gs2-krb5 gssapi plain
    ```
4. 修改`/etc/ldap/ldap.conf`，增加下面内容：
    ```
    SASL_MECH GSSAPI
    ```
5. 重启`openldap`服务器。
6. 为用户设置密码， `echo -n {SASL}username@7V1.NET|base64`
    ```sh
ldapmodify -Q -Y EXTERNAL -H ldapi:/// <<EOF
dn: $USER_DN
changetype: modify
replace: userPassword
userPassword:: `echo -n {SASL}username@7V1.NET|base64`
EOF
```

## 其实干货在文章的最后

这么复杂的操作，好痛苦，怎么破？别怕，我们有Docker大法。

### OpenLDAP篇

1. 从github上将docker-openldap克隆下来，地址为`https://github.com/lifei/docker-openldap`，
执行构建命令`docker build .`。
2. 使用新构建的镜像来启动一个容器， `docker run --name=openldap -d lifei/openldap`，
就这样一个`OpenLDAP`服务就启起来了。
3. 进入这个镜像进行配置， 执行命令`docker exec -it openldap bash`，进入`bash`。
4. 这个镜像采用环境变量作为配置项，先准备如下面的内容：
    ```sh
    export NAME=7v1
    export DOMAIN_DN=dc=7v1,dc=net
    export ADMIN_DN=cn=admin,$DOMAIN_DN
    export ADMIN_PW=1234
    export KRB5REALM=7V1.NET
    export DOMAIN_REALM=7v1.net
    ```
    以上变量含义比较清晰，就不再解释了。
5. 执行初始化`OpenLDAP`的命令`openldap-init.sh`，`OpenLDAP`服务就按照上面的配置初始化好了。
6. 若`Kerberos`想使用`OpenLDAP`作为后端存储，则只需执行`Kerberos`初始化命令，`kerberos-init.sh`，
`Kerberos`所需要的设置也配置完毕了。
7. 未完待续，等`Kerberos`配置完毕后，再来配置使用`Kerberos`作为`OpenLDAP`的校验。

### Kerberos篇

1. 从github上将docker-kerberos克隆下来，地址为`https://github.com/lifei/docker-kerberos`，
执行构建命令`docker build .`。
2. 使用新构建的镜像来启动一个容器， `docker run --link openldap:openldap --name=kerberos -d lifei/kerberos`，
就这样一个`Kerberos`容器就启起来了，但是与上面的`OpenLDAP`不同，此时的`Kerberos`服务还未启动。
3. 进入这个镜像进行配置， 执行命令`docker exec -it kerberos bash`，进入`bash`。
4. 这个镜像同样采用环境变量作为配置项，先准备如下面的内容：
    ```sh
    export DOMAIN_DN=dc=7v1,dc=net
    export ADMIN_DN=cn=admin,$DOMAIN_DN
    export ADMIN_PW=1234
    export KRB5REALM=7V1.NET
    export DOMAIN_REALM=7v1.net
    export LDAP_HOST=openldap
    ```
5. 执行初始化命令`kerberos-init.sh`，键入`Master Key`的密码两次，`Kerberos`环境就配置完了。
6. 若想让OpenLDAP使用Kerberos作为验证方法的话，在执行`kadmin.local -q "ank root/admin"`，
键入密码，生成一个可以使用`kadmin`命令的账号，下文的`krb5-init.sh`会用到这个账号。

### OpenLDAP使用Kerberos作为验证方法

1. 在openldap容器中设置环境命令`export KDC_ADDRESS=kerberos容器的IP`。
2. 执行`krb5-init.sh`，初始化`krb5.conf`文件并为ldap服务器生成两个principal。
3. 重启openldap容器，创建测试账号`smith`
```sh
# openldap容器中执行
UID=smith && ldapadd -x -D $ADMIN_DN -w $ADMIN_PW <<EOF
dn: ou=people,$DOMAIN_DN
objectClass: organizationalUnit
ou: people

dn: cn=$UID,ou=people,$DOMAIN_DN
objectclass: inetOrgPerson
sn: $UID
uid: $UID
userpassword: {SASL}$UID@$KRB5REALM
description: $UID
ou: people
EOF

kadmin -q "ank smith"

ldapwhoami -x -D cn=smith,ou=people,$DOMAIN_DN -W
```

## 参考资料：
1. http://www.math.ucla.edu/~jimc/documents/ldap/kerberos-ldap-1202.html
2. http://www.math.ucla.edu/~jimc/documents/ldap/ldap-setup-1202.html
3. http://labs.opinsys.com/blog/2010/03/16/openldap-authentication-with-kerberos-backend-using-sasl/
4. http://www.rjsystems.nl/en/2100-kerberos-openldap-provider.php
5. http://web.mit.edu/kerberos/krb5-1.13/doc/admin/conf_ldap.html
