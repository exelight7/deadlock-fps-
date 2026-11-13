import sys
if __name__ == '__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--firewall-plan':
        from deadlock_fps.firewall import helper_main
        try:helper_main(sys.argv[2])
        except Exception as error:
            print(str(error),file=sys.stderr);sys.exit(1)
    else:
        from deadlock_fps import i18n
        i18n.load()  # before the interface is imported: many strings are built at import time
        from deadlock_fps.ui import main
        main()
