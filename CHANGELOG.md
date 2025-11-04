# CHANGELOG

<!-- version list -->

## v1.2.0 (2025-11-04)

### Bug Fixes

- Add persistence for initiative overlay ui
  ([`2db301a`](https://github.com/MoonlitMoo/GM-Assistant/commit/2db301a317495cd05843ca26af47fa3b7cdc9fad))

- Adding icon for the window
  ([`b6c0dfb`](https://github.com/MoonlitMoo/GM-Assistant/commit/b6c0dfb19664fde3a2a419539c454206ceea874e))

- Correctly reopens after spontaneous close
  ([`1a26d9c`](https://github.com/MoonlitMoo/GM-Assistant/commit/1a26d9c5f965348dfe32185f25d6921b9a7f35b2))

- Initiative overlay scales correctly from settings
  ([`912b01c`](https://github.com/MoonlitMoo/GM-Assistant/commit/912b01c1df3e8e53ee5b2175765887c4e022e9f6))

- Pass bring to front via display state
  ([`b0f88b8`](https://github.com/MoonlitMoo/GM-Assistant/commit/b0f88b848927651f611732dc07a30167dd01f575))

- Run the subprocess correctly while packaged
  ([`fa93fc5`](https://github.com/MoonlitMoo/GM-Assistant/commit/fa93fc5af1efdceb54f72781ed87adef0094f798))

- Show initiative persistence on player window
  ([`483443d`](https://github.com/MoonlitMoo/GM-Assistant/commit/483443d98284e051020a4e96178c1c7cfbe3b9d3))

### Features

- Adding initiative overlay params to settings
  ([`3e6d967`](https://github.com/MoonlitMoo/GM-Assistant/commit/3e6d967c29edba9e3c56eb41240a5910aba3057c))

- Adding separate taskbar item for player window
  ([`fb8c3e9`](https://github.com/MoonlitMoo/GM-Assistant/commit/fb8c3e9ac873b0dd722cfb721e0f681048e7fa1f))

- Run player window as a subprocess
  ([`6d00c2c`](https://github.com/MoonlitMoo/GM-Assistant/commit/6d00c2c179a14a310f8e90b4aea963efa46d460d))

### Refactoring

- Initiative data into dataclass for ease
  ([`2980403`](https://github.com/MoonlitMoo/GM-Assistant/commit/298040353b1076a0632f5efc52b5ca03c4588502))

- Move display state to core +
  ([`d0a55a3`](https://github.com/MoonlitMoo/GM-Assistant/commit/d0a55a3a7db46daa2be6d0d55f0b6923b01120dd))

- Rename display state to specify player
  ([`7808fe4`](https://github.com/MoonlitMoo/GM-Assistant/commit/7808fe41c75db4aa0abeb39c22a0236efa3418f2))


## v1.1.0 (2025-10-21)

### Bug Fixes

- Add create actions to context menu
  ([`28b4afb`](https://github.com/MoonlitMoo/GM-Assistant/commit/28b4afb5933b2d1ee9250df23d200c8443953375))

- Persistance synced between image and player windows
  ([`01f7b9a`](https://github.com/MoonlitMoo/GM-Assistant/commit/01f7b9a14837106cd3d3997835b28e6ef2fe258d))

- Player window is now companion window
  ([`ff9c79f`](https://github.com/MoonlitMoo/GM-Assistant/commit/ff9c79f0694566265aa9b702a28026122df9e0d4))

- Reorder image logic
  ([`9f93247`](https://github.com/MoonlitMoo/GM-Assistant/commit/9f9324764d13fc68b2f92b8436df467e12a39f2f))

- Resize the initiative tab elements to be more readable
  ([`0a121da`](https://github.com/MoonlitMoo/GM-Assistant/commit/0a121daa39e426940ed1df0422194db92b529abd))

- Sorting applied count > name + hex colour swatch
  ([`a505d54`](https://github.com/MoonlitMoo/GM-Assistant/commit/a505d543d3574ff6681f94c79ee58d9598a2cb5f))

- Update build script
  ([`35186c7`](https://github.com/MoonlitMoo/GM-Assistant/commit/35186c7abd75b37f1351b6618a94d24ff5958fc0))

- Wrong sizing of initiative labels
  ([`9b8099e`](https://github.com/MoonlitMoo/GM-Assistant/commit/9b8099e1e16bda20d26b2285253f8c0ba7136f89))

### Features

- Add tag strip for images
  ([`3f42a4f`](https://github.com/MoonlitMoo/GM-Assistant/commit/3f42a4f34d5381ec57eb862a80de596951018702))

- Adding initiative tab
  ([`f3f8de4`](https://github.com/MoonlitMoo/GM-Assistant/commit/f3f8de43c8a4d59e2801237a055ee426b17469c2))

- Adding manage tag dialog
  ([`34dc4fb`](https://github.com/MoonlitMoo/GM-Assistant/commit/34dc4fbf8c6a3fbeb2ece217d8faffbb92a6132e))

- Adding persistance to initiative list
  ([`c4e5ebd`](https://github.com/MoonlitMoo/GM-Assistant/commit/c4e5ebd6998591779855f215ff8070a4fc75e0fa))

- Adding Tag and ImageTagLink models to the database
  ([`b498457`](https://github.com/MoonlitMoo/GM-Assistant/commit/b4984571d1247ac6b8b3f7eafb252a8fbcc84c44))

- Adding tagging service and repo
  ([`d12109a`](https://github.com/MoonlitMoo/GM-Assistant/commit/d12109a50a8bac61494a3da2de7a75e575720799))

- Hooking initiative display into player window
  ([`4e4df2f`](https://github.com/MoonlitMoo/GM-Assistant/commit/4e4df2f973f6fc3bdee188468d93cf197dc07a63))

### Refactoring

- Change to parchment style
  ([`31b35ac`](https://github.com/MoonlitMoo/GM-Assistant/commit/31b35ac4f71693bd9302ac5178080b7d60f7743f))

- Clean up persist logic and handling
  ([`9ed088f`](https://github.com/MoonlitMoo/GM-Assistant/commit/9ed088f465932172e67f7e8e98ac964e563e3e9e))

- Move db under dmt dir
  ([`58789eb`](https://github.com/MoonlitMoo/GM-Assistant/commit/58789eb17c60d8dedb1a5122062b08b5817fd08c))

- Move initiative overlay to separate widget
  ([`000ab35`](https://github.com/MoonlitMoo/GM-Assistant/commit/000ab358a48f7ad8dcd25d8bc3bb23a6db3591db))

- Reorganise initiative tab + add round passthrough
  ([`086b8ee`](https://github.com/MoonlitMoo/GM-Assistant/commit/086b8eed32b24be29cbdb6d65a92ea623582d55a))

- Shift database access to repo class from service
  ([`3fcc878`](https://github.com/MoonlitMoo/GM-Assistant/commit/3fcc878a39eec82ec3b9f50121e121c8346831e6))

### Testing

- Refactor important to conftest
  ([`90b5e86`](https://github.com/MoonlitMoo/GM-Assistant/commit/90b5e8623e6cab52423f8ca8d592455eb97238f7))

- Split db setup fixtures to new file
  ([`1384e93`](https://github.com/MoonlitMoo/GM-Assistant/commit/1384e93a1ae1d66aec51ef72bbeacd5c99197114))


## v1.0.0 (2025-09-25)

- Initial Release
