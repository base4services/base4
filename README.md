
# Base4


### **ToDo**

...

### **Installation**

The base4 package is installed using the pip command

Since this repository is private, you need to have access to it, or it needs to be shared with you

The installation of base4 is done using the following command

```bash
pip install git+ssh://git@github.com/digital-cube/base4.git
```

If you want to develop base4 features within your project, you need to create a lib directory, check out base4 from git into it, and install it using the -e flag

```bash
pip install -e ./lib/base4
```

If you previously installed it from git with the first command (which will happen if you do pip -r requirements), uninstall it

Don't forget that if base is changed, and local installation is not connected in the dockers, all dockers should be rebuilt

